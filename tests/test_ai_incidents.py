import importlib.util
import io
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("incidents", ROOT / "tools" / "ai_incidents.py")
incidents = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(incidents)


def record(source_id="source-1", title="Test incident"):
    return incidents.ManualOOFIncidentAdapter().normalize({
        "title": title,
        "eventType": "Incident",
        "severity": "High",
        "evidenceConfidence": "Verified",
        "publicationStatus": "Monitored",
        "source": {
            "sourceId": source_id,
            "publisher": "Test Authority",
            "url": f"https://example.test/{source_id}",
            "verificationStatus": "Verified",
        },
    })


class IncidentDomainTests(unittest.TestCase):
    def test_stable_identity(self):
        self.assertEqual(record()["id"], record()["id"])

    def test_duplicate_sources_merge_into_one_incident(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = incidents.FileIncidentRepository(Path(temporary) / "store.json")
            first = record("source-1")
            second = record("source-2")
            second["id"] = incidents.stable_incident_id("source-2")
            repository.upsert_sources([first, second])
            stored = repository.list()
            self.assertEqual(len(stored), 1)
            self.assertEqual(len(stored[0]["sources"]), 2)

    def test_public_projection_rejects_unknown_architecture_identity(self):
        item = record()
        item["architectureRelevance"] = {
            "status": "ARCHITECTURE_IDENTIFIED",
            "classification": "Automated",
            "primaryArchitectureId": "invented",
            "secondaryArchitectureIds": [],
        }
        result = incidents.public_records([item])[0]
        self.assertEqual(result["architectureRelevance"]["status"], "ARCHITECTURE_REVIEW_REQUIRED")
        self.assertIsNone(result["architectureRelevance"]["primaryArchitectureId"])

    def test_aiid_snapshot_keeps_provenance_and_can_be_enriched(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Incidents"
        sheet.append(["AI Incident Database export"])
        sheet.append(["INCIDENT IDENTITY"])
        sheet.append(["Incident ID", "date", "title", "description", "deployer", "Country Code", "Location Region"])
        sheet.append([1702, datetime(2026, 9, 10), "Source title", "Source description", "Source organization", "US", "North America"])
        output = io.BytesIO()
        workbook.save(output)
        adapter = incidents.AIIDWeeklyExcelAdapter(
            workbook_bytes=output.getvalue(),
            snapshot_url="https://example.test/AIID_Excel_Export-20260921.xlsx",
        )
        raw = adapter.fetch_new_records(None)
        normalized = adapter.normalize(raw[0])
        enriched = incidents.enrich_incident(normalized)
        self.assertEqual(normalized["title"], "Source title")
        self.assertEqual(normalized["summary"], "Source description")
        self.assertEqual(normalized["countryCode"], "US")
        self.assertEqual(enriched["architectureRelevance"]["status"], "ARCHITECTURE_IDENTIFIED")
        self.assertEqual(enriched["architectureRelevance"]["primaryArchitectureId"], "aig")
        self.assertEqual(normalized["sources"][0]["url"], "https://incidentdatabase.ai/cite/1702")
        self.assertEqual(normalized["sources"][0]["retrievedAt"], "2026-09-21T00:00:00Z")

    def test_country_and_architecture_are_inferred_from_incident_context(self):
        item = record(title="License plate reader misread a plate in New Mexico")
        item["summary"] = "The automated system produced an incorrect match."
        item["country"] = None
        item["countryCode"] = None
        item["system"] = "Automated License Plate Reader"
        enriched = incidents.enrich_incident(item)
        self.assertEqual(enriched["countryCode"], "US")
        self.assertEqual(enriched["country"], "United States of America")
        self.assertEqual(enriched["architectureRelevance"]["primaryArchitectureId"], "validos")
        self.assertEqual(enriched["architectureRelevance"]["architectureIndexState"], "VALIDOS®")

    def test_unresolved_country_is_explicit_without_fabricating_location(self):
        item = record(title="Generic AI system incident")
        enriched = incidents.enrich_incident(item)
        self.assertEqual(enriched["country"], "Location not specified")
        self.assertIsNone(enriched["countryCode"])

    def test_country_names_prefer_sovereign_name_and_leave_ambiguous_names_unresolved(self):
        self.assertEqual(incidents._country_names()["AU"], "Australia")
        item = record(title="An incident was reported in Georgia")
        enriched = incidents.enrich_incident(item)
        self.assertEqual(enriched["country"], "Location not specified")
        self.assertIsNone(enriched["countryCode"])


if __name__ == "__main__":
    unittest.main()
