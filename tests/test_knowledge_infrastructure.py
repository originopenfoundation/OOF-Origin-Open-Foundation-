import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from query_knowledge_registry import KnowledgeRegistry  # noqa: E402
from build_knowledge_infrastructure import cross_validate_architecture, git_value, source_hash  # noqa: E402
from validate_json_schema import validate_instance  # noqa: E402


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

    def test_governed_resolution_accepts_trademark_variants(self):
        architecture = next(item for item in self.registry.objects if item.get("artifactType") == "Architecture" and item.get("acronym"))
        plain = self.registry.resolve(architecture["acronym"])
        trademarked = self.registry.resolve(f"{architecture['acronym']}®")
        self.assertEqual(plain["status"], "FOUND")
        self.assertEqual(trademarked["status"], "FOUND")
        self.assertEqual(plain["object"]["id"], trademarked["object"]["id"])
        self.assertNotIn(plain["resolutionConfidence"], {None, ""})
        self.assertTrue(plain["sourceAuthority"])

    def test_typo_and_unknown_queries_do_not_create_canonical_facts(self):
        architecture = next(item for item in self.registry.objects if item.get("artifactType") == "Architecture" and item.get("acronym"))
        typo = self.registry.resolve(f"{architecture['acronym']}x")
        self.assertIn(typo["status"], {"CANDIDATE_MATCH", "AMBIGUOUS"})
        self.assertIsNone(typo["object"])
        unknown = self.registry.resolve("ZZZ-NOT-AN-OOF-OBJECT")
        self.assertEqual(unknown["status"], "UNKNOWN")
        self.assertIsNone(unknown["object"])

    def test_aliases_have_provenance_and_only_governed_aliases_resolve(self):
        entries = [entry for values in self.registry.aliases.values() for entry in values]
        self.assertTrue(entries)
        self.assertTrue(all(entry.get("provenance") for entry in entries))
        candidate_entries = [entry for entry in entries if entry.get("aliasType") == "candidate_alias"]
        self.assertTrue(all(entry.get("resolverEligible") is False for entry in candidate_entries))

    def test_compact_object_preserves_identity_and_relationships(self):
        architecture = next(item for item in self.registry.objects if item.get("artifactType") == "Architecture")
        result = self.registry.compact(architecture["id"])
        self.assertEqual(result["status"], "FOUND")
        compact = result["compactObject"]
        self.assertEqual(compact["objectId"], architecture["id"])
        self.assertEqual(compact["canonicalUrl"], architecture["canonicalUrl"])
        self.assertIn("authoritativeRelationships", compact)

    def test_external_ai_suite_covers_a_through_w(self):
        report = self.registry.external_ai_test_suite()
        self.assertEqual(report["caseCount"], 23)
        self.assertEqual(report["failed"], 0)
        self.assertEqual(report["passed"], 23)
        conflict = next(item for item in report["cases"] if item["name"].startswith("W "))
        self.assertEqual(conflict["resultState"], "CANONICAL_PRECEDENCE")

    def test_resolution_benchmark_is_reported_in_milliseconds(self):
        architecture = next(item for item in self.registry.objects if item.get("artifactType") == "Architecture")
        benchmark = self.registry.benchmark(architecture["id"])
        self.assertEqual(set(benchmark), {"objectId", "canonicalName", "acronym", "canonicalUrl", "relationship", "lexical", "fuzzyCandidate"})
        self.assertTrue(all(value >= 0 for value in benchmark.values()))

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

    def test_candidate_review_covers_every_detected_collision(self):
        report = json.loads((ROOT / "data" / "knowledge" / "reports" / "candidate-entity-review.json").read_text(encoding="utf-8"))
        self.assertEqual(report["candidatePoolCount"], report["candidateGroupCount"])
        self.assertEqual(report["candidateGroupCount"], len(report["groups"]))

    def test_provenance_uses_each_source_files_commit(self):
        for item in self.registry.representations:
            provenance = item["provenance"]
            self.assertEqual(provenance["repositoryCommit"], git_value("%H", provenance["sourcePath"]))

    def test_schema_date_time_requires_time_and_timezone(self):
        schema = {"type": "string", "format": "date-time"}
        schema_path = ROOT / "schemas" / "oof-knowledge-manifest.v1.schema.json"
        self.assertTrue(validate_instance("2026-09-30", schema, schema_path))
        self.assertTrue(validate_instance("2026-09-30T10:30:00", schema, schema_path))
        self.assertFalse(validate_instance("2026-09-30T10:30:00Z", schema, schema_path))

    def test_source_hash_is_platform_independent(self):
        lf_record = {"source": "<html>\n<body>OOF</body>\n</html>\n"}
        crlf_record = {"source": lf_record["source"].replace("\n", "\r\n")}
        self.assertEqual(source_hash(lf_record), source_hash(crlf_record))


if __name__ == "__main__":
    unittest.main()
