from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TrafficIntegrityTests(unittest.TestCase):
    def test_single_cloudflare_beacon_is_loaded_without_client_identifiers(self) -> None:
        header = (ROOT / "header.js").read_text(encoding="utf-8")
        self.assertEqual(header.count("https://static.cloudflareinsights.com/beacon.min.js"), 1)
        self.assertIn("document.querySelector('script[data-cf-beacon]')", header)
        self.assertNotIn("document.cookie", header)
        self.assertNotIn("localStorage", header)

    def test_heat_map_preserves_raw_data_and_does_not_apply_country_exclusions(self) -> None:
        dataset = json.loads((ROOT / "data" / "oof-global-interest-heat-map.json").read_text(encoding="utf-8"))
        self.assertFalse(dataset["technicalTraffic"]["cloudflareBotFilter"])
        self.assertEqual(dataset["technicalTraffic"]["additionalExclusions"], [])
        self.assertEqual(dataset["trafficViews"]["raw"]["countryData"], "countries")
        self.assertEqual(dataset["trafficViews"]["qualityAdjusted"]["status"], "unavailable")

    def test_maps_reserve_layout_space_before_data_arrives(self) -> None:
        heat_map_css = (ROOT / "style.css").read_text(encoding="utf-8")
        incident_css = (ROOT / "assets" / "css" / "oof-ai-incidents.css").read_text(encoding="utf-8")
        self.assertIn("min-height: 620px", heat_map_css)
        self.assertIn("contain: layout paint", heat_map_css)
        self.assertIn("min-height: 460px", incident_css)
        self.assertIn("contain: layout paint", incident_css)


if __name__ == "__main__":
    unittest.main()
