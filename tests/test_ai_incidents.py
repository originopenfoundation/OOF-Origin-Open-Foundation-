import importlib.util
import io
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("incidents", ROOT / "tools" / "ai_incidents.py")
incidents = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(incidents)
ENGINE_SPEC = importlib.util.spec_from_file_location("incident_intelligence_v2", ROOT / "tools" / "incident_intelligence_v2.py")
engine = importlib.util.module_from_spec(ENGINE_SPEC)
ENGINE_SPEC.loader.exec_module(engine)


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

    def test_v3_analysis_is_separate_versioned_and_never_implicitly_approved(self):
        original = (ROOT / "data" / "ai-incidents" / "incident-store.json").read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            analysis_path = temporary / "analysis.json"
            snapshot_path = temporary / "snapshot.json"
            first = engine.build(analysis_path=analysis_path, snapshot_path=snapshot_path, created_at="2026-10-02T12:00:00Z")
            analysis_after_first = analysis_path.read_bytes()
            snapshot_after_first = snapshot_path.read_bytes()
            second = engine.build(analysis_path=analysis_path, snapshot_path=snapshot_path, created_at="2026-10-02T13:00:00Z")
            assessments = json.loads(analysis_path.read_text(encoding="utf-8"))["assessments"]
            self.assertEqual(first["assessmentsCreated"], 252)
            self.assertEqual(second["assessmentsCreated"], 0)
            self.assertEqual(analysis_path.read_bytes(), analysis_after_first)
            self.assertEqual(snapshot_path.read_bytes(), snapshot_after_first)
            self.assertTrue(all(item["analysisType"] == "Automated" for item in assessments))
            self.assertTrue(all(item["humanReview"]["status"] == "Not performed" for item in assessments))
            self.assertTrue(all(item["oofApproved"] is False for item in assessments))
            self.assertTrue(all(item["assessmentConfidence"] in {"High", "Moderate", "Limited", "Evidence Insufficient"} for item in assessments))
            self.assertTrue(all(1 <= len(item["governanceQuestions"]) <= 5 for item in assessments))
        self.assertEqual((ROOT / "data" / "ai-incidents" / "incident-store.json").read_bytes(), original)

    def test_v3_consumes_dynamic_knowledge_architecture(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            objects = {
                "objects": [
                    {
                        "id": "OOF-KO-ARCH-TEST", "canonicalName": "TEST™ Identity Governance Architecture",
                        "acronym": "TEST", "artifactType": "Architecture", "authorityState": "CANONICAL_AUTHORITATIVE",
                        "canonicalUrl": "https://example.test/test", "governedSpace": "Identity and Origin",
                    },
                    {
                        "id": "OOF-KO-STD-TEST-1", "canonicalName": "Identity Provenance Standard",
                        "acronym": "IPS", "artifactType": "ParentStandard", "authorityState": "CANONICAL_AUTHORITATIVE",
                        "architectureId": "OOF-KO-ARCH-TEST", "governedSpace": "Identity provenance and impersonation",
                    },
                ]
            }
            (root / "objects-core.json").write_text(json.dumps(objects), encoding="utf-8")
            (root / "relationships.json").write_text(json.dumps({"relationships": []}), encoding="utf-8")
            (root / "manifest.json").write_text(json.dumps({"buildId": "TEST-KNOWLEDGE-1"}), encoding="utf-8")
            knowledge = engine.KnowledgeLayer(root)
            ranked = knowledge.rank({"title": "Deepfake impersonation incident", "summary": "Identity was fabricated."})
            self.assertEqual(ranked[0]["architectureId"], "test")

    def test_v3_assignments_are_explainable_and_source_linked(self):
        latest = engine.latest_assessments()
        self.assertEqual(len(latest), 252)
        for assessment in latest.values():
            architecture = assessment["architectureAnalysis"]
            assignments = [architecture.get("primaryArchitecture"), *architecture.get("contributingArchitectures", [])]
            for assignment in filter(None, assignments):
                self.assertTrue(assignment["reasonForRelevance"])
                self.assertTrue(assignment["supportingEvidence"])

    def test_v3_assessment_separates_evidence_findings_and_gaps(self):
        item = record(title="Deepfake impersonation caused a reported fraud")
        item["summary"] = "A public report says a cloned voice was used to impersonate an executive."
        item["country"] = "United States of America"
        item["countryCode"] = "US"
        assessment = engine.build_assessment(item, engine.KnowledgeLayer(), 1, None, "test", "2026-10-03T00:00:00Z")
        self.assertEqual(assessment["assessmentLabel"], "Automated Preliminary Governance Assessment")
        self.assertIn(assessment["assessmentConfidence"], {"High", "Moderate", "Limited", "Evidence Insufficient"})
        self.assertTrue(assessment["incidentEvidence"]["reportedClaims"])
        self.assertTrue(assessment["incidentEvidence"]["knownFacts"])
        self.assertTrue(assessment["evidenceGaps"])
        self.assertFalse(assessment["oofApproved"])
        self.assertIn("not an official investigation", assessment["assessmentDisclosure"])

    def test_v3_architecture_roles_and_findings_are_traceable(self):
        item = record(title="Autonomous deepfake agent made an incorrect prediction")
        item["summary"] = "An autonomous agent used a cloned identity and produced an incorrect predictive decision."
        item["system"] = "Autonomous predictive agent"
        assessment = engine.build_assessment(item, engine.KnowledgeLayer(), 1, None, "test", "2026-10-03T00:00:00Z")
        architecture = assessment["architectureAnalysis"]
        assigned = [architecture.get("primaryArchitecture"), *architecture.get("contributingArchitectures", [])]
        assigned = [value for value in assigned if value]
        self.assertTrue(assigned)
        self.assertEqual(assigned[0]["role"], "Primary")
        self.assertTrue(all(value["whyItMattersHere"] and value["governanceFocus"] for value in assigned))
        self.assertTrue(all(finding["evidenceBasis"] and finding["architectureReference"] for finding in assessment["governanceFindings"]))


if __name__ == "__main__":
    unittest.main()
