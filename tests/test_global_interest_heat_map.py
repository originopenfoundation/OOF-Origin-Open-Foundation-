from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from update_global_interest_heat_map import classify, resolve_iso


def row(country: str, day: str, visits: float) -> dict:
    return {
        "dimensions": {"countryName": country, "date": day},
        "sum": {"visits": visits},
    }


class GlobalInterestHeatMapTests(unittest.TestCase):
    def test_resolve_iso_accepts_codes_and_country_names_but_excludes_antarctica(self) -> None:
        names = {"slovakia": "SK", "antarctica": "AQ"}
        self.assertEqual(resolve_iso("sk", names), "SK")
        self.assertEqual(resolve_iso("Slovakia", names), "SK")
        self.assertIsNone(resolve_iso("AQ", names))
        self.assertIsNone(resolve_iso("Antarctica", names))

    def test_classification_uses_population_and_reliability_thresholds(self) -> None:
        now = datetime(2026, 9, 23, tzinfo=timezone.utc)
        rows = [
            row("AA", "2026-09-10", 10),
            row("AA", "2026-09-11", 10),
            row("AA", "2026-09-17", 10),
            row("AA", "2026-09-18", 10),
            row("BB", "2026-09-10", 5),
            row("BB", "2026-09-17", 5),
            row("CC", "2026-09-17", 50),
        ]
        populations = {"AA": 1_000_000, "BB": 100_000_000, "CC": 1_000_000}

        public, internal = classify(rows, populations, {}, now)

        self.assertEqual(public, [
            {"iso": "AA", "status": "high"},
            {"iso": "BB", "status": "emerging"},
        ])
        self.assertEqual(internal["BB"]["classification"], "emerging")
        self.assertEqual(internal["CC"]["classification"], "insufficient")
        self.assertIn("normalizedScore", internal["AA"])
        for country in public:
            self.assertNotIn("visits", country)
            self.assertNotIn("population", country)


if __name__ == "__main__":
    unittest.main()
