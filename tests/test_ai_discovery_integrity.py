import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "ai_discovery_integrity", ROOT / "tools" / "evaluate_ai_discovery_integrity.py"
)
integrity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(integrity)


class AiDiscoveryIntegrityTests(unittest.TestCase):
    def test_source_resolver_preserves_authority_boundaries(self):
        registry = integrity.KnowledgeRegistry()
        supporting = registry.resolve_source(
            "https://originopenfoundation.org/content/d/ai-agent-authority-verification.html"
        )
        canonical = registry.resolve_source(
            "https://originopenfoundation.org/content/a/asga-architecture.html"
        )
        unknown = registry.resolve_source("OOF fabricated methodology TEST-001")
        self.assertEqual(supporting["status"], "FOUND")
        self.assertEqual(supporting["claimState"], "SOURCE_AUTHENTICITY_ONLY")
        self.assertEqual(canonical["claimState"], "CANONICAL_METHODOLOGY_REFERENCE")
        self.assertEqual(unknown["status"], "UNKNOWN")

    def test_local_integrity_evaluation_covers_all_required_case_types(self):
        report = integrity.evaluate()
        self.assertEqual(report["caseCount"], 50)
        self.assertEqual(report["passed"], 50)
        self.assertEqual(report["failed"], 0)
        self.assertEqual(
            set(report["caseTypeCounts"]),
            {"POSITIVE", "EVIDENCE_BOUNDARY", "AUTHORITY_BOUNDARY", "AMBIGUOUS", "NEGATIVE", "ADVERSARIAL", "VERSION_INTEGRITY", "CONTRADICTORY_SOURCE", "INTEGRATION"},
        )
        self.assertEqual(report["externalEvaluationStatus"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
