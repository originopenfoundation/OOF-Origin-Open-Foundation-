#!/usr/bin/env python3
"""Verify the public map dataset matches the validated artifact after deployment."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import time
import urllib.error
import urllib.request

from validate_global_interest_heat_map import DEFAULT_DATASET, freshness_state, parse_timestamp, validate

PUBLIC_URL = "https://originopenfoundation.org/data/oof-global-interest-heat-map.json"
MAX_BYTES = 5 * 1024 * 1024


def matches_publication(expected: bytes, actual: bytes, now: datetime) -> bool:
    """Do not accept stale, future-dated, truncated or different public output."""
    if len(expected) > MAX_BYTES or len(actual) > MAX_BYTES:
        return False
    try:
        expected_payload = json.loads(expected)
        payload = json.loads(actual)
        if payload != expected_payload:
            return False
        observed = parse_timestamp(payload.get("lastSuccessfulCloudflareRetrievalAt"), "retrieval")
        return observed <= now + timedelta(minutes=10) and freshness_state(payload, now) == "current"
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


def retrieve_public() -> bytes:
    request = urllib.request.Request(PUBLIC_URL, headers={"User-Agent": "OOF-heat-map-publication-check/1.0",
                                                          "Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=12) as response:
        if response.status != 200 or response.geturl() != PUBLIC_URL:
            raise ValueError("Unexpected public dataset response or redirect")
        return response.read(MAX_BYTES + 1)


def verify(expected_path: Path, max_wait: int = 360, interval: int = 10) -> bool:
    if max_wait < 0 or interval < 1:
        raise ValueError("Invalid verification timing")
    validate(expected_path)
    expected = expected_path.read_bytes()
    deadline = time.monotonic() + max_wait
    while True:
        try:
            if matches_publication(expected, retrieve_public(), datetime.now(timezone.utc)):
                print("Verified: live public dataset matches the validated fresh dataset.")
                return True
        except (OSError, ValueError, urllib.error.URLError):
            pass
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            print("Public dataset did not match the validated fresh dataset within the allowed time.")
            return False
        time.sleep(min(interval, remaining))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--max-wait", type=int, default=360)
    args = parser.parse_args()
    raise SystemExit(0 if verify(args.dataset, max_wait=args.max_wait) else 1)
