#!/usr/bin/env python3
"""Validate the public OOF Governance Space Map payload."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "oof-global-interest-heat-map.json"
REQUIRED_TOP_LEVEL = {
    "schemaVersion", "algorithmVersion", "windowStart", "windowEnd", "generatedAt", "lastCheckedAt",
    "dataRevision", "source", "observationUnit", "technicalTraffic", "canonicalArchitectureSource",
    "countries", "governanceSpaces",
}
STATUSES = {"very-high", "high", "moderate", "emerging"}
MOMENTUM = {"rapidly-rising", "rising", "stable", "declining"}
FORBIDDEN_KEYS = {
    "visitors", "visitorCount", "sessions", "sessionCount", "population",
    "rawEngagement", "normalizedScore", "score", "reliabilityScore",
    "analyticsId", "deviceId", "userId", "ip", "ipAddress", "uniquePeople", "uniqueUsers"
}


def parse_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO-8601 string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def freshness_state(payload: dict, now: datetime | None = None) -> str:
    checked = parse_timestamp(payload["lastCheckedAt"], "lastCheckedAt")
    reference = now or datetime.now(timezone.utc)
    return "stale" if reference - checked > timedelta(hours=36) else "current"


def validate(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if set(payload) != REQUIRED_TOP_LEVEL:
        raise ValueError(f"Public payload fields differ from the governed schema: {sorted(set(payload) ^ REQUIRED_TOP_LEVEL)}")
    for field in ("windowStart", "windowEnd", "generatedAt", "lastCheckedAt"):
        parse_timestamp(payload[field], field)
    if payload["schemaVersion"] != "1.1" or payload["algorithmVersion"] != "3.0":
        raise ValueError("Unsupported Governance Space Map schema or algorithm version")
    if not re.fullmatch(r"[a-f0-9]{64}", str(payload["dataRevision"])):
        raise ValueError("dataRevision must be a SHA-256 value")
    if payload["source"] != "Cloudflare Web Analytics":
        raise ValueError("Unexpected analytics source")
    if "not unique people" not in payload["observationUnit"].casefold():
        raise ValueError("Public metadata must distinguish visits from unique people")
    technical = payload["technicalTraffic"]
    if not isinstance(technical, dict) or technical.get("cloudflareBotFilter") is not True:
        raise ValueError("Technical traffic policy must declare the verified Cloudflare bot filter")
    if payload["canonicalArchitectureSource"] != "data/oof-architecture-registry.json":
        raise ValueError("Unexpected Canonical Architecture Index source")
    countries = payload["countries"]
    if not isinstance(countries, list):
        raise ValueError("countries must be an array")
    seen: set[str] = set()
    for index, country in enumerate(countries):
        if not isinstance(country, dict):
            raise ValueError(f"countries[{index}] must be an object")
        extras = set(country) - {"iso", "status", "momentum"}
        forbidden = set(country) & FORBIDDEN_KEYS
        if extras or forbidden:
            raise ValueError(f"countries[{index}] exposes unsupported fields: {sorted(extras | forbidden)}")
        iso = country.get("iso")
        if not isinstance(iso, str) or not re.fullmatch(r"[A-Z]{2}", iso):
            raise ValueError(f"countries[{index}].iso must be an ISO alpha-2 code")
        if iso in seen:
            raise ValueError(f"Duplicate country code: {iso}")
        if iso == "AQ":
            raise ValueError("Antarctica must not be published in the interest heat map")
        seen.add(iso)
        if country.get("status") not in STATUSES:
            raise ValueError(f"Invalid public status for {iso}")
        if "momentum" in country and country["momentum"] not in MOMENTUM:
            raise ValueError(f"Invalid momentum for {iso}")
    spaces = payload["governanceSpaces"]
    if not isinstance(spaces, list) or not spaces:
        raise ValueError("governanceSpaces must contain synchronized canonical entries")
    space_ids: set[str] = set()
    for index, space in enumerate(spaces):
        if set(space) != {"id", "acronym", "name", "url"}:
            raise ValueError(f"governanceSpaces[{index}] has unsupported fields")
        if not all(isinstance(space[field], str) and space[field] for field in space):
            raise ValueError(f"governanceSpaces[{index}] contains an empty field")
        if space["id"] in space_ids:
            raise ValueError(f"Duplicate governance space: {space['id']}")
        if space["url"].startswith(("http://", "https://")) or space["url"].startswith("/"):
            raise ValueError(f"Governance space URL must be a repository-relative public URL: {space['id']}")
        space_ids.add(space["id"])
    serialized = json.dumps(payload, ensure_ascii=False)
    leaked = [key for key in FORBIDDEN_KEYS if f'"{key}"' in serialized]
    if leaked:
        raise ValueError(f"Public payload exposes forbidden fields: {sorted(leaked)}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_DATASET)
    args = parser.parse_args()
    payload = validate(args.path)
    print(f"Governance Space Map dataset valid: {len(payload['countries'])} classified countries and {len(payload['governanceSpaces'])} canonical governance spaces")


if __name__ == "__main__":
    main()
