import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from verify_global_interest_internal import verify_consistency


class InternalConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.internal = {"algorithmVersion": "4.0", "generatedAt": "time", "dataWindowStart": "start",
                         "dataWindowEnd": "end", "countryCoverage": {"sourceCountries": 2,
                         "classifiedCountries": 1, "unresolvedCountries": []},
                         "countries": {"AA": {"activityTotal": 21, "dailyAverage": 3, "classification": "emerging"},
                                       "BB": {"activityTotal": 7, "dailyAverage": 1, "classification": "insufficient"}}}
        self.public = {"algorithmVersion": "4.0", "generatedAt": "time", "windowStart": "start",
                       "windowEnd": "end", "countries": [{"iso": "AA", "status": "emerging"}]}

    def test_valid_coverage_and_unresolved_flag(self):
        self.assertFalse(verify_consistency(self.internal, self.public))
        self.internal["countryCoverage"]["unresolvedCountries"] = ["Unknown"]
        self.assertTrue(verify_consistency(self.internal, self.public))

    def test_tampered_classification_missing_country_and_bad_average_fail(self):
        for change in ("classification", "missing", "average", "window", "duplicate"):
            with self.subTest(change=change):
                internal, public = copy.deepcopy(self.internal), copy.deepcopy(self.public)
                if change == "classification": public["countries"][0]["status"] = "high"
                if change == "missing": public["countries"] = []
                if change == "average": internal["countries"]["AA"]["dailyAverage"] = 4
                if change == "window": internal["dataWindowEnd"] = "other"
                if change == "duplicate": public["countries"].append(public["countries"][0])
                with self.assertRaises(ValueError): verify_consistency(internal, public)


if __name__ == "__main__":
    unittest.main()
