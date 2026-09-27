import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from query_knowledge_registry import KnowledgeRegistry  # noqa: E402


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
        self.assertIsNone(self.manifest["generatedAt"])


if __name__ == "__main__":
    unittest.main()
