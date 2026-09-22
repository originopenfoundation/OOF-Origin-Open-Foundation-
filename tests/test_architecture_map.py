import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("architecture_registry", ROOT / "tools" / "build_architecture_registry.py")
registry_builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(registry_builder)


class ArchitectureMapTests(unittest.TestCase):
    def test_index_is_the_source_of_truth(self):
        architectures = registry_builder.parse_index()
        self.assertGreaterEqual(len(architectures), 14)
        self.assertEqual(len(architectures), len({item["acronym"] for item in architectures}))
        self.assertTrue(all(item["standards"] for item in architectures))
        self.assertTrue(all(item["source"] == "oof-structured-architecture-index.html" for item in architectures))

    def test_navigation_targets_exist(self):
        architectures = registry_builder.parse_index()
        registry_builder.parse_navigation(architectures)
        self.assertEqual(registry_builder.validate(architectures), [])

    def test_published_and_development_states_do_not_overlap(self):
        registry = json.loads((ROOT / "data" / "oof-architecture-registry.json").read_text(encoding="utf-8"))
        completed = {item["acronym"] for item in registry["architectures"]}
        development = {item["acronym"] for item in registry["developmentArchitectures"]}
        self.assertFalse(completed & development)
        self.assertTrue(all(item["status"] == "completed" for item in registry["architectures"]))

    def test_new_index_entries_require_approval(self):
        detected = {item["acronym"] for item in registry_builder.parse_index()}
        approved = set(registry_builder.read_json(registry_builder.APPROVED_PATH, {"approved": []})["approved"])
        audit = json.loads(registry_builder.AUDIT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(set(audit["pendingApproval"]), detected - approved)


if __name__ == "__main__":
    unittest.main()
