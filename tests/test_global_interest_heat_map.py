from __future__ import annotations

import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from update_global_interest_heat_map import (  # noqa: E402
    TECHNICAL_TRAFFIC_POLICY,
    atomic_write,
    canonical_governance_spaces,
    cloudflare_rows,
    classify,
    public_payload,
    resolve_iso,
)
from validate_global_interest_heat_map import FORBIDDEN_KEYS, freshness_state, validate  # noqa: E402


NOW = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)


def row(country: str, day: str, visits: float) -> dict:
    return {"dimensions": {"countryName": country, "date": day}, "sum": {"visits": visits}}


def distributed(country: str, visits: list[float], spacing: int = 1) -> list[dict]:
    start = datetime(2026, 9, 17, tzinfo=timezone.utc)
    return [row(country, (start + timedelta(days=index * spacing)).date().isoformat(), value) for index, value in enumerate(visits)]


class GlobalInterestHeatMapTests(unittest.TestCase):
    def classify_one(self, rows: list[dict], population: int = 1_000_000):
        public, internal = classify(rows, {"AA": population}, {}, NOW)
        return public, internal["AA"]

    def test_resolve_iso_accepts_codes_and_country_names_but_excludes_antarctica(self) -> None:
        names = {"slovakia": "SK", "antarctica": "AQ"}
        self.assertEqual(resolve_iso("sk", names), "SK")
        self.assertEqual(resolve_iso("Slovakia", names), "SK")
        self.assertIsNone(resolve_iso("AQ", names))
        self.assertIsNone(resolve_iso("Antarctica", names))

    def test_fewer_than_three_visits_is_insufficient(self) -> None:
        public, internal = self.classify_one(distributed("AA", [1, 1], spacing=3))
        self.assertEqual(public, [])
        self.assertEqual(internal["classification"], "insufficient")

    def test_three_visits_on_one_day_is_insufficient(self) -> None:
        public, internal = self.classify_one(distributed("AA", [3]))
        self.assertEqual(public, [])
        self.assertEqual(internal["classification"], "insufficient")

    def test_three_visits_across_two_days_is_emerging(self) -> None:
        public, _ = self.classify_one(distributed("AA", [2, 1], spacing=3))
        self.assertEqual(public, [{"iso": "AA", "status": "emerging"}])

    def test_concentrated_repetition_cannot_create_very_high(self) -> None:
        public, internal = self.classify_one(distributed("AA", [55, 5], spacing=10))
        self.assertNotEqual(public[0]["status"], "very-high")
        self.assertGreater(internal["maximumDailyShare"], 0.45)

    def test_distributed_recurrence_receives_more_effective_signal(self) -> None:
        _, concentrated = self.classify_one(distributed("AA", [32, 32], spacing=10))
        _, distributed_state = self.classify_one(distributed("AA", [8] * 8, spacing=2))
        self.assertGreater(distributed_state["effectiveVisits"], concentrated["effectiveVisits"])

    def test_very_high_is_not_awarded_without_independent_conditions(self) -> None:
        public, _ = self.classify_one(distributed("AA", [7] * 6, spacing=2))
        self.assertNotEqual(public[0]["status"], "very-high")

    def test_very_high_is_awarded_when_all_conditions_are_satisfied(self) -> None:
        public, _ = self.classify_one(distributed("AA", [8] * 8, spacing=2))
        self.assertEqual(public[0]["status"], "very-high")

    def test_verified_technical_traffic_policy_excludes_cloudflare_bots_only(self) -> None:
        self.assertTrue(TECHNICAL_TRAFFIC_POLICY["cloudflareBotFilter"])
        self.assertEqual(TECHNICAL_TRAFFIC_POLICY["additionalExclusions"], [])
        self.assertIn("do not reliably identify individual people", TECHNICAL_TRAFFIC_POLICY["limitation"])
        response = {"data": {"viewer": {"accounts": [{"rows": []}]}}}
        with patch("update_global_interest_heat_map.request_json", return_value=response) as request:
            cloudflare_rows("a" * 32, "b" * 32, "token", NOW - timedelta(days=14), NOW)
        query = request.call_args.kwargs["payload"]["query"]
        self.assertIn("bot: 0", query)

    def test_stale_dataset_detection_uses_36_hour_boundary(self) -> None:
        payload = {"lastCheckedAt": "2026-09-29T12:00:00Z"}
        self.assertEqual(freshness_state(payload, NOW), "current")
        self.assertEqual(freshness_state(payload, NOW + timedelta(hours=13)), "stale")

    def test_failed_refresh_preserves_last_valid_dataset(self) -> None:
        source = ROOT / "data" / "oof-global-interest-heat-map.json"
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "dataset.json"
            target.write_bytes(source.read_bytes())
            before = target.read_bytes()
            with self.assertRaises(ValueError):
                atomic_write(target, {"countries": []})
            self.assertEqual(target.read_bytes(), before)

    def test_public_payload_contains_no_private_fields(self) -> None:
        payload = json.loads((ROOT / "data" / "oof-global-interest-heat-map.json").read_text(encoding="utf-8"))
        validate(ROOT / "data" / "oof-global-interest-heat-map.json")
        serialized = json.dumps(payload)
        for key in FORBIDDEN_KEYS:
            self.assertNotIn(f'"{key}"', serialized)

    def test_canonical_architecture_index_synchronization(self) -> None:
        spaces = canonical_governance_spaces()
        registry = json.loads((ROOT / "data" / "oof-architecture-registry.json").read_text(encoding="utf-8"))
        self.assertEqual({item["id"] for item in spaces}, {item["id"] for item in registry["architectures"] if item["status"] == "completed"})

    def test_unavailable_canonical_source_fails_safely(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.json"
            with self.assertRaises(FileNotFoundError):
                canonical_governance_spaces(missing)

    def test_unchanged_revision_still_refreshes_public_metadata(self) -> None:
        spaces = canonical_governance_spaces()
        payload = public_payload([{"iso": "AA", "status": "emerging"}], spaces, NOW - timedelta(days=14), NOW)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "dataset.json"
            self.assertTrue(atomic_write(target, payload))
            later = public_payload(payload["countries"], spaces, NOW - timedelta(days=13), NOW + timedelta(days=1))
            self.assertEqual(payload["dataRevision"], later["dataRevision"])
            self.assertTrue(atomic_write(target, later))
            refreshed = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(refreshed["lastCheckedAt"], later["lastCheckedAt"])
            self.assertEqual(refreshed["windowStart"], later["windowStart"])
            self.assertFalse(atomic_write(target, later))


if __name__ == "__main__":
    unittest.main()
