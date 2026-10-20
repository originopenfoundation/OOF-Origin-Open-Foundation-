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
        expected = len(incidents.public_records(incidents.FileIncidentRepository().list()))
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            analysis_path = temporary / "analysis.json"
            snapshot_path = temporary / "snapshot.json"
            first = engine.build(analysis_path=analysis_path, snapshot_path=snapshot_path, created_at="2026-10-02T12:00:00Z")
            analysis_after_first = analysis_path.read_bytes()
            snapshot_after_first = snapshot_path.read_bytes()
            report_path = temporary / "v3-backfill-report.json"
            report_after_first = report_path.read_bytes()
            second = engine.build(analysis_path=analysis_path, snapshot_path=snapshot_path, created_at="2026-10-02T13:00:00Z")
            assessments = json.loads(analysis_path.read_text(encoding="utf-8"))["assessments"]
            self.assertEqual(first["assessmentsCreated"], expected)
            self.assertEqual(second["assessmentsCreated"], 0)
            self.assertEqual(analysis_path.read_bytes(), analysis_after_first)
            self.assertEqual(snapshot_path.read_bytes(), snapshot_after_first)
            self.assertEqual(report_path.read_bytes(), report_after_first)
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

    def test_v3_methodology_depth_is_evidence_gated_and_hierarchical(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            objects = {"objects": [
                {"id": "ARCH", "canonicalName": "Identity Architecture", "acronym": "ID", "artifactType": "Architecture", "authorityState": "CANONICAL_AUTHORITATIVE", "canonicalUrl": "https://example.test/arch"},
                {"id": "STD", "canonicalName": "Identity Provenance Standard", "artifactType": "ParentStandard", "authorityState": "CANONICAL_AUTHORITATIVE", "architectureId": "ARCH", "canonicalUrl": "https://example.test/std", "governedSpace": "identity provenance impersonation"},
                {"id": "MOD", "canonicalName": "Impersonation Evidence Module", "artifactType": "CoreModule", "authorityState": "CANONICAL_AUTHORITATIVE", "architectureId": "ARCH", "parentObjectId": "STD", "canonicalUrl": "https://example.test/mod", "governedSpace": "identity provenance impersonation evidence"},
            ]}
            (root / "objects-core.json").write_text(json.dumps(objects), encoding="utf-8")
            (root / "relationships.json").write_text(json.dumps({"relationships": []}), encoding="utf-8")
            (root / "manifest.json").write_text(json.dumps({"buildId": "TEST"}), encoding="utf-8")
            knowledge = engine.KnowledgeLayer(root)
            sparse = knowledge.references("ARCH", {"title": "Identity impersonation report"})
            rich = knowledge.references("ARCH", {
                "title": "Identity impersonation evidence report", "summary": "Identity provenance evidence showed impersonation.",
                "system": "Identity system", "technology": "identity evidence classifier", "organization": "Test operator",
            })
            self.assertEqual(sparse, [])
            self.assertEqual([item["artifactType"] for item in rich], ["ParentStandard", "CoreModule"])
            self.assertEqual(rich[1]["parentObjectId"], rich[0]["objectId"])

    def test_v3_assessment_exposes_complete_methodological_reasoning_chain(self):
        item = record(title="Deepfake impersonation caused a reported fraud")
        item["summary"] = "A cloned identity and voice were used to impersonate an executive."
        item["system"] = "Voice cloning system"
        assessment = engine.build_assessment(item, engine.KnowledgeLayer(), 1, None, "test", "2026-10-09T00:00:00Z")
        chain = assessment["methodologicalReasoningChain"]
        self.assertEqual(chain["incidentEvidence"], ["source-1"])
        self.assertEqual(chain["primaryArchitecture"], assessment["architectureAnalysis"]["primaryArchitecture"]["objectId"])
        self.assertIn(chain["deepestJustifiedLevel"], {"Architecture", "ParentStandard", "CoreModule"})
        self.assertEqual(chain["governanceQuestions"], assessment["governanceQuestions"])

    def test_v3_assignments_are_explainable_and_source_linked(self):
        latest = engine.latest_assessments()
        expected = len(incidents.public_records(incidents.FileIncidentRepository().list()))
        self.assertEqual(len(latest), expected)
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

    def test_v3_normalization_removes_placeholders_and_parses_serialized_industry(self):
        item = record(title="Automated system report")
        item["system"] = "no"
        item["industry"] = '["public administration", "law enforcement"]'
        normalized, provenance = engine.normalized_incident_view(item)
        self.assertIsNone(normalized["system"])
        self.assertEqual(normalized["industry"], "public administration; law enforcement")
        self.assertFalse(provenance["sourceRecordModified"])
        self.assertEqual(item["system"], "no")
        self.assertEqual(item["industry"], '["public administration", "law enforcement"]')

    def test_v3_placeholder_values_never_reach_questions_or_evidence_terms(self):
        item = record(title="Automated reporting incident")
        item["summary"] = "A public report described an automated outcome."
        item["system"] = "no"
        item["industry"] = '["public administration"]'
        assessment = engine.build_assessment(item, engine.KnowledgeLayer(), 1, None, "test", "2026-10-11T00:00:00Z")
        questions = " ".join(assessment["governanceQuestions"]).casefold()
        terms = {
            term.casefold()
            for assignment in [assessment["architectureAnalysis"].get("primaryArchitecture"), *assessment["architectureAnalysis"].get("contributingArchitectures", [])]
            if assignment for term in assignment.get("matchedTerms", [])
        }
        self.assertNotIn("how no produced", questions)
        self.assertNotIn("no", terms)

    def test_v341_semantic_noise_values_are_not_used_as_generated_subjects(self):
        item = record(title="Semantic noise regression case")
        item["summary"] = "The source report uses ordinary prose that mentions yes and whether."
        item["system"] = "yes"
        assessment = engine.build_assessment(item, engine.KnowledgeLayer(), 1, None, "test", "2026-10-20T00:00:00Z")
        generated = " ".join([assessment["incidentGovernanceInsight"] or "", *assessment["governanceQuestions"]]).casefold()
        self.assertNotIn("how yes", generated)
        self.assertEqual(assessment["qualityOutcomes"]["semanticIntegrity"], "PASS")
        self.assertEqual(assessment["qualityOutcomes"]["publicationEligibility"], "PUBLISHABLE")

    def test_v3_exposes_three_independent_confidence_dimensions(self):
        item = record(title="Deepfake impersonation report")
        item["summary"] = "A cloned voice reportedly impersonated an executive."
        assessment = engine.build_assessment(item, engine.KnowledgeLayer(), 1, None, "test", "2026-10-11T00:00:00Z")
        self.assertEqual(set(assessment["confidenceDimensions"]), {
            "sourceCorroboration", "extractionCompleteness", "methodologicalAssignment",
        })
        self.assertFalse(assessment["sourceNormalization"]["sourceRecordModified"])

    def test_v34_adds_evidence_bounded_report_and_prevention_guidance(self):
        item = record(title="Deepfake impersonation report")
        item["summary"] = "A cloned voice reportedly impersonated an executive."
        assessment = engine.build_assessment(item, engine.KnowledgeLayer(), 1, None, "test", "2026-10-15T00:00:00Z")
        self.assertIn(assessment["evidenceSnapshot"]["publicEvidenceStatus"], {
            "Source-Reported", "Independently Corroborated", "Officially Documented",
            "Evidence Insufficient", "Contradicted / Disputed",
        })
        self.assertIn("reports that", assessment["oofIncidentReport"]["report"])
        self.assertTrue(assessment["preventionGuidance"]["recommendedPreventiveControl"])
        self.assertEqual(len(assessment["practicalChecklist"]), 4)
        self.assertFalse(assessment["oofApproved"])

    def test_candidate_queue_is_persistent_deduplicated_and_daily_limited(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            queue_path = temporary / "queue.json"
            repository = incidents.FileIncidentRepository(temporary / "store.json")
            candidates = [record(f"source-{index}", f"Incident {index}") for index in range(12)]
            first = incidents.queue_candidates(candidates, repository.list(), queue_path)
            second = incidents.queue_candidates(candidates, repository.list(), queue_path)
            processed = incidents.process_candidate_queue(repository, limit=10, path=queue_path)
            self.assertEqual(first["added"], 12)
            self.assertEqual(second["added"], 0)
            self.assertEqual(processed["processed"], 10)
            self.assertEqual(processed["remaining"], 2)
            self.assertEqual(len(repository.list()), 10)

    def test_country_geometry_codes_cover_france_without_duplicate_primary_codes(self):
        geojson = json.loads((ROOT / "assets" / "data" / "ne_50m_admin_0_countries.geojson").read_text(encoding="utf-8"))
        resolved = []
        for feature in geojson["features"]:
            properties = feature.get("properties") or {}
            primary = properties.get("ISO_A2") or properties.get("iso_a2")
            extended = properties.get("ISO_A2_EH") or properties.get("iso_a2_eh")
            code = extended if primary == "-99" else primary
            if code and code != "-99":
                resolved.append(str(code).upper())
        self.assertIn("FR", resolved)
        store = json.loads((ROOT / "data" / "ai-incidents" / "incident-store.json").read_text(encoding="utf-8"))
        incident_codes = {item.get("countryCode") for item in store["incidents"] if item.get("countryCode")}
        self.assertFalse(incident_codes - set(resolved))

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

    def test_public_export_is_complete_lightweight_and_valid(self):
        result = incidents.validate_public_export()
        summary = incidents.read_json(incidents.PUBLIC_ROOT / "summary.json", {})
        index = incidents.read_json(incidents.PUBLIC_ROOT / "incident-index.json", {})
        first_page = incidents.read_json(incidents.PUBLIC_ROOT / "incidents-page-1.json", {})
        self.assertEqual(result["incidents"], summary["totalIncidents"])
        self.assertEqual(len(index["items"]), summary["totalIncidents"])
        self.assertLessEqual(len(first_page["items"]), 25)
        self.assertNotIn("automatedAnalysis", first_page["items"][0])
        self.assertTrue(first_page["items"][0]["detailUrl"].startswith("/ai-incidents/incidents/"))
        representative = index["items"][:20]
        self.assertEqual(len(representative), 20)
        for item in representative:
            detail = incidents.read_json(incidents.PUBLIC_ROOT / "incident-details" / f"{item['slug']}.json", {})
            self.assertEqual(detail["id"], item["id"])
            self.assertTrue(item["source"]["url"].startswith("https://"))
        dates = [item.get("occurredAt") or item.get("reportedAt") or "" for item in representative]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_public_export_rejects_missing_detail_projection(self):
        with tempfile.TemporaryDirectory() as temporary:
            original_root = incidents.PUBLIC_ROOT
            try:
                incidents.PUBLIC_ROOT = Path(temporary)
                incidents.write_json(incidents.PUBLIC_ROOT / "summary.json", {"totalIncidents": 1})
                incidents.write_json(incidents.PUBLIC_ROOT / "incident-index.json", {"items": [{
                    "id": "OOF-AII-TEST", "slug": "missing", "title": "Missing detail",
                    "detailUrl": "/ai-incidents/incidents/missing/", "source": {"url": "https://example.test/source"},
                }]})
                with self.assertRaisesRegex(ValueError, "missing its public detail projection"):
                    incidents.validate_public_export()
            finally:
                incidents.PUBLIC_ROOT = original_root

    def test_public_export_rejects_duplicate_identity_and_malformed_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            original_root = incidents.PUBLIC_ROOT
            try:
                incidents.PUBLIC_ROOT = Path(temporary)
                bad = {
                    "id": "OOF-AII-DUPLICATE", "slug": "duplicate", "title": "Duplicate",
                    "detailUrl": "/ai-incidents/incidents/duplicate/", "source": {"url": "not-a-url"},
                }
                incidents.write_json(incidents.PUBLIC_ROOT / "summary.json", {"totalIncidents": 2})
                incidents.write_json(incidents.PUBLIC_ROOT / "incident-index.json", {"items": [bad, bad]})
                with self.assertRaisesRegex(ValueError, "duplicate incident IDs"):
                    incidents.validate_public_export()
            finally:
                incidents.PUBLIC_ROOT = original_root


if __name__ == "__main__":
    unittest.main()
