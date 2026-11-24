#!/usr/bin/env python3
"""Verify private country aggregation against the public classification output.

Read only runner-local diagnostics. Never print country counts or thresholds.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re

from validate_global_interest_heat_map import DEFAULT_DATASET, validate


def verify_consistency(internal: dict, public: dict) -> bool:
    if not isinstance(internal, dict) or not isinstance(public, dict):
        raise ValueError("Invalid diagnostics")
    if (internal.get("algorithmVersion") != "4.0" or public.get("algorithmVersion") != "4.0"
            or internal.get("generatedAt") != public.get("generatedAt")
            or internal.get("dataWindowStart") != public.get("windowStart")
            or internal.get("dataWindowEnd") != public.get("windowEnd")):
        raise ValueError("Diagnostic and public dataset metadata differ")
    countries, coverage, published = internal.get("countries"), internal.get("countryCoverage"), public.get("countries")
    if not isinstance(countries, dict) or not isinstance(coverage, dict) or not isinstance(published, list):
        raise ValueError("Incomplete country coverage")
    expected = {}
    for iso, entry in countries.items():
        if not re.fullmatch(r"[A-Z]{2}", iso) or not isinstance(entry, dict):
            raise ValueError("Invalid diagnostic country")
        total, average = entry.get("activityTotal"), entry.get("dailyAverage")
        if (type(total) not in (int, float) or not math.isfinite(total) or total < 0
                or type(average) not in (int, float) or not math.isfinite(average)
                or not math.isclose(average, total / 7, rel_tol=1e-12, abs_tol=1e-12)):
            raise ValueError("Invalid country aggregation")
        status = ("very-high" if average >= 80 else "high" if average >= 40 else
                  "moderate" if average >= 20 else "emerging" if average >= 3 else "insufficient")
        if entry.get("classification") != status:
            raise ValueError("Country classification does not match its diagnostic")
        if status != "insufficient":
            expected[iso] = status
    actual = {}
    for entry in published:
        if not isinstance(entry, dict) or entry.get("iso") in actual:
            raise ValueError("Invalid published country")
        actual[entry.get("iso")] = entry.get("status")
    if actual != expected or coverage.get("sourceCountries") != len(countries) or coverage.get("classifiedCountries") != len(expected):
        raise ValueError("Public country coverage does not match source diagnostics")
    if not isinstance(coverage.get("unresolvedCountries"), list):
        raise ValueError("Country resolution diagnostics unavailable")
    return bool(coverage["unresolvedCountries"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--internal", required=True, type=Path)
    parser.add_argument("--dataset", default=DEFAULT_DATASET, type=Path)
    args = parser.parse_args()
    public = validate(args.dataset)
    unresolved = verify_consistency(json.loads(args.internal.read_text(encoding="utf-8")), public)
    print("Verified: classified countries agree with the private aggregation diagnostics.")
    if unresolved:
        print("Notice: some source country identifiers could not be resolved; no classification was invented.")
