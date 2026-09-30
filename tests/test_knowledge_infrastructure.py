import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from query_knowledge_registry import KnowledgeRegistry  # noqa: E402
from build_knowledge_infrastructure import cross_validate_architecture  # noqa: E402


class KnowledgeInfrastructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = KnowledgeRegistry()
        cls.manifest = json.loads((ROOT / "data" / "knowledge" / "manifest.json").read_text(encoding="utf-8"))

    def test_exact_id_and_url_lookup_match(self):
        item = self.registry.objects[0]
        self.assertEqual(self.registry.exact(item["id"])["id"], item["id"])
        self.assertEqual(self.registry.exact(item["canonicalUrl"])["id"], item["id"])

    def test_lexical_lookup_is_deterministic(self):
        first = self.registry.lexical("Validation Governance Architecture", 5)
        second = self.registry.lexical("Validation Governance Architecture", 5)
        self.assertEqual(first, second)
        self.assertTrue(first)

    def test_authoritative_filter_excludes_discovery_links(self):
        architecture = self.registry.exact("OOF-KO-ARCH-VALIDOS")
        relationships = self.registry.related(architecture["id"], authoritative_only=True)
        self.assertTrue(relationships)
        self.assertTrue(all(item["authorityState"] == "AUTHORITATIVE" for item in relationships))

    def test_manifest_is_public_report_only(self):
        self.assertEqual(self.manifest["generationMode"], "report-only")
        self.assertEqual(self.manifest["visibility"], "public")
        self.assertEqual(self.manifest["schemaVersion"], "1.1")
        self.assertIsNotNone(self.manifest["generatedAt"])

    def test_exact_lookup_reports_ambiguity_and_negative_result(self):
        self.assertEqual(self.registry.exact_result("definitely-not-an-oof-object")["status"], "NOT_FOUND")
        duplicated = next((name for name, ids in self.registry.by_name.items() if len(ids) > 1), None)
        if duplicated:
            self.assertEqual(self.registry.exact_result(duplicated)["status"], "AMBIGUOUS")

    def test_review_and_quarantine_are_excluded_from_retrieval(self):
        self.assertTrue(all(item["object"]["authorityState"] not in {"REVIEW_REQUIRED", "QUARANTINED"} for item in self.registry.lexical("governance", 100)))

    def test_future_architecture_onboarding_and_correction(self):
        fixture = json.loads((ROOT / "tests" / "fixtures" / "knowledge" / "architecture-onboarding.v1.json").read_text(encoding="utf-8"))
        architecture = fixture["base"]
        for case in fixture["cases"]:
            candidate = {**architecture, **case["override"]}
            result = cross_validate_architecture(architecture, candidate)
            self.assertEqual(result["result"], case["expectedResult"], case["name"])
            self.assertEqual(result["authorityState"], case["expectedAuthorityState"], case["name"])
        corrected = {**architecture, "acronym": "TEST"}
        self.assertEqual(cross_validate_architecture(architecture, corrected)["authorityState"], "CANONICAL_AUTHORITATIVE")

    def test_supporting_lookup_returns_only_citable_material(self):
        results = self.registry.supporting("governance", 20)
        self.assertTrue(results)
        self.assertTrue(all(item["authorityState"] == "SUPPORTING_CITABLE" for item in results))


if __name__ == "__main__":
    unittest.main()
