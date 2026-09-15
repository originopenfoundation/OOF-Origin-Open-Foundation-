#!/usr/bin/env python3
"""Build the public Heat Map payload from aggregated Cloudflare Web Analytics data."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from validate_global_interest_heat_map import validate


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DATASET = ROOT / "data" / "oof-global-interest-heat-map.json"
INTEREST_ALGORITHM_VERSION = "2.0"
GRAPHQL_URL = "https://api.cloudflare.com/client/v4/graphql"
HOST = "originopenfoundation.org"
WINDOW_DAYS = 14


def request_json(url: str, *, token: str | None = None, payload: dict | None = None) -> object:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json", "User-Agent": "OOF-Global-Interest-Heat-Map/1.0"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, headers=headers, method="POST" if body else "GET")
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def cloudflare_rows(account_id: str, site_tag: str, token: str, start: datetime, end: datetime) -> list[dict]:
    if not re.fullmatch(r"[a-fA-F0-9]{32}", account_id):
        raise ValueError("CLOUDFLARE_ACCOUNT_ID must be a 32-character hexadecimal ID")
    if not re.fullmatch(r"[a-fA-F0-9]{32}", site_tag):
        raise ValueError("CLOUDFLARE_WEB_ANALYTICS_SITE_TAG must be a 32-character hexadecimal ID")
    start_value = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_value = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    query = f'''query {{
      viewer {{
        accounts(filter: {{ accountTag: "{account_id}" }}) {{
          rows: rumPageloadEventsAdaptiveGroups(
            limit: 10000
            orderBy: [sum_visits_DESC]
            filter: {{ AND: [
              {{ datetime_geq: "{start_value}", datetime_leq: "{end_value}" }}
              {{ siteTag: "{site_tag}" }}
              {{ requestHost: "{HOST}" }}
              {{ bot: 0 }}
            ] }}
          ) {{
            sum {{ visits }}
            dimensions {{ countryName date }}
          }}
        }}
      }}
    }}'''
    result = request_json(GRAPHQL_URL, token=token, payload={"query": query, "variables": {}})
    if not isinstance(result, dict) or result.get("errors"):
        raise RuntimeError(f"Cloudflare Analytics query failed: {result.get('errors') if isinstance(result, dict) else result}")
    accounts = result.get("data", {}).get("viewer", {}).get("accounts", [])
    if not accounts:
        raise RuntimeError("Cloudflare Analytics returned no account data")
    return accounts[0].get("rows", [])


def resolve_iso(value: str) -> str | None:
    candidate = (value or "").strip()
    if re.fullmatch(r"[A-Za-z]{2}", candidate):
        return candidate.upper()
    return None


def classify(rows: list[dict], now: datetime) -> tuple[list[dict], dict]:
    countries: dict[str, dict] = defaultdict(lambda: {"visits": 0.0, "days": set(), "daily": defaultdict(float)})
    for row in rows:
        dimensions = row.get("dimensions") or {}
        iso = resolve_iso(str(dimensions.get("countryName") or ""))
        if not iso:
            continue
        visits = float((row.get("sum") or {}).get("visits") or 0)
        if visits <= 0:
            continue
        day = str(dimensions.get("date") or "")[:10]
        countries[iso]["visits"] += visits
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
            countries[iso]["days"].add(day)
            countries[iso]["daily"][day] += visits

    peak_visits = max((metrics["visits"] for metrics in countries.values()), default=0)
    public: list[dict] = []
    internal: dict[str, dict] = {}
    recent_start = (now - timedelta(days=7)).date().isoformat()
    prior_start = (now - timedelta(days=14)).date().isoformat()
    for iso, metrics in sorted(countries.items()):
        record = {
            "visits": round(metrics["visits"], 4),
            "activeDays": len(metrics["days"]),
            "classification": "emerging",
        }
        relative_interest = metrics["visits"] / peak_visits if peak_visits else 0
        status = "high" if relative_interest >= 0.5 else "moderate" if relative_interest >= 0.2 else "emerging"
        item = {"iso": iso, "status": status}
        recent = sum(value for day, value in metrics["daily"].items() if day >= recent_start)
        prior = sum(value for day, value in metrics["daily"].items() if prior_start <= day < recent_start)
        recent_days = sum(1 for day in metrics["daily"] if day >= recent_start)
        prior_days = sum(1 for day in metrics["daily"] if prior_start <= day < recent_start)
        if recent >= 8 and prior >= 8 and recent_days >= 3 and prior_days >= 3:
            ratio = recent / prior
            item["momentum"] = "rapidly-rising" if ratio >= 1.8 else "rising" if ratio >= 1.2 else "declining" if ratio <= 0.75 else "stable"
        public.append(item)
        record["classification"] = status
        record["relativeInterest"] = round(relative_interest, 8)
        record["recentVisits"] = round(recent, 4)
        record["priorVisits"] = round(prior, 4)
        internal[iso] = record
    return public, internal


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, delete=False, suffix=".tmp") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        temporary = Path(stream.name)
    validate(temporary)
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--internal-output", type=Path)
    args = parser.parse_args()
    account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    site_tag = os.environ["CLOUDFLARE_WEB_ANALYTICS_SITE_TAG"]
    token = os.environ["CLOUDFLARE_ANALYTICS_API_TOKEN"]
    now = datetime.now(timezone.utc).replace(microsecond=0)
    start = now - timedelta(days=WINDOW_DAYS)
    rows = cloudflare_rows(account_id, site_tag, token, start, now)
    public_countries, internal_countries = classify(rows, now)
    public_payload = {"generatedAt": now.isoformat().replace("+00:00", "Z"), "countries": public_countries}
    atomic_write(PUBLIC_DATASET, public_payload)
    if args.internal_output:
        args.internal_output.parent.mkdir(parents=True, exist_ok=True)
        args.internal_output.write_text(json.dumps({
            "generatedAt": public_payload["generatedAt"],
            "dataWindowStart": start.isoformat().replace("+00:00", "Z"),
            "dataWindowEnd": public_payload["generatedAt"],
            "algorithmVersion": INTEREST_ALGORITHM_VERSION,
            "countries": internal_countries,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Published {len(public_countries)} reliable country classifications from {len(rows)} aggregate rows")


if __name__ == "__main__":
    main()
