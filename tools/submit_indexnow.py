#!/usr/bin/env python3
"""Submit canonical OOF URLs to IndexNow when deployment secrets are available."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://api.indexnow.org/indexnow"
HOST = "originopenfoundation.org"
SITEMAP_NAMESPACE = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def read_sitemap_urls() -> list[str]:
    """Return canonical URLs from the generated XML sitemap."""
    sitemap = ElementTree.parse(ROOT / "sitemap.xml")
    return [
        location.text.strip()
        for location in sitemap.findall("sm:url/sm:loc", SITEMAP_NAMESPACE)
        if location.text and location.text.strip()
    ]


def key_location_for(key: str) -> str:
    """Return the canonical public validation URL for an IndexNow key."""
    return f"https://{HOST}/{key}.txt"


def key_file_is_valid(key: str) -> bool:
    """Confirm that the deployed static key file is present in this release."""
    key_file = ROOT / f"{key}.txt"
    return key_file.is_file() and key_file.read_text(encoding="utf-8").strip() == key


def submit_payload(payload: dict[str, object], retries: int, retry_delay_seconds: int) -> int:
    """Submit once the newly published verification file is visible to IndexNow."""
    request = Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=30) as response:
                print(f"IndexNow response: HTTP {response.status}")
                return 0
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace").strip()
            retryable = error.code in {403, 429, 500, 502, 503, 504}
            if retryable and attempt < retries:
                print(
                    f"IndexNow response: HTTP {error.code}; retrying in {retry_delay_seconds}s "
                    f"({attempt + 1}/{retries}). {detail}"
                )
                sleep(retry_delay_seconds)
                continue
            print(f"IndexNow response: HTTP {error.code}. {detail}")
            return 1
        except URLError as error:
            if attempt < retries:
                print(
                    f"IndexNow network error; retrying in {retry_delay_seconds}s "
                    f"({attempt + 1}/{retries}). {error.reason}"
                )
                sleep(retry_delay_seconds)
                continue
            print(f"IndexNow network error: {error.reason}")
            return 1
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--retry-delay-seconds", type=int, default=30)
    args = parser.parse_args()
    key = os.environ.get("INDEXNOW_KEY", "").strip()
    if not key:
        print("IndexNow skipped: INDEXNOW_KEY is not configured.")
        return 0
    if not key_file_is_valid(key):
        print(f"IndexNow configuration error: {key}.txt is missing or does not contain the configured key.")
        return 1
    urls = read_sitemap_urls()
    payload = {
        "host": HOST,
        "key": key,
        "keyLocation": key_location_for(key),
        "urlList": urls[:10000],
    }
    if args.dry_run:
        print(
            f"IndexNow payload ready for {len(payload['urlList'])} URLs "
            f"with verification at {payload['keyLocation']}."
        )
        return 0
    return submit_payload(payload, max(args.retries, 0), max(args.retry_delay_seconds, 0))


if __name__ == "__main__":
    sys.exit(main())
