import importlib.util
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ai_discovery_guides", ROOT / "tools" / "build_ai_discovery_guides.py")
guides = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guides)


class AiDiscoveryGuideTests(unittest.TestCase):
    def test_five_problem_oriented_guides_are_defined(self):
        self.assertEqual(len(guides.GUIDES), 5)
        self.assertEqual(len({guide["slug"] for guide in guides.GUIDES}), 5)
        self.assertTrue(all(len(guide["faq"]) >= 2 for guide in guides.GUIDES))
        self.assertTrue(all(len(guide["examples"]) >= 2 for guide in guides.GUIDES))

    def test_evaluation_harness_has_fifty_unfabricated_queries(self):
        dataset = guides.build_evaluation_dataset()
        self.assertEqual(dataset["queryCount"], 50)
        self.assertEqual(len(dataset["queries"]), 50)
        self.assertTrue(all(query["evaluationStatus"] == "NOT_RUN" for query in dataset["queries"]))
        self.assertTrue(all(query["recommendationAccuracy"] is None for query in dataset["queries"]))
        self.assertTrue(all(query["expectedCanonicalUrls"] for query in dataset["queries"]))
        self.assertTrue(all(query["verificationRequirements"] for query in dataset["queries"]))
        self.assertTrue(all(query["expectedAnswerStructure"]["mustIdentify"] for query in dataset["queries"]))
        self.assertTrue(all(query["expectedAssessmentPathway"]["status"] in {"AVAILABLE", "FUTURE"} for query in dataset["queries"]))
        self.assertEqual(Counter(query["category"] for query in dataset["queries"]), Counter({guide["title"]: 10 for guide in guides.GUIDES}))

    def test_guides_have_a_truthful_assessment_pathway(self):
        for guide in guides.GUIDES:
            assessment = guide["assessment"]
            self.assertIn(assessment["status"], {"available", "future"})
            self.assertTrue(assessment["verification"])
            if assessment["status"] == "available":
                self.assertTrue(assessment["href"])
                self.assertTrue((ROOT / "content" / assessment["href"].removeprefix("../")).is_file())
            else:
                self.assertIsNone(assessment["href"])

    def test_generated_pages_link_to_available_canonical_sources(self):
        for guide in guides.GUIDES:
            page = ROOT / "content" / "d" / f"{guide['slug']}.html"
            self.assertTrue(page.is_file(), page)
            source = page.read_text(encoding="utf-8")
            self.assertIn('"@type":"FAQPage"', source)
            self.assertIn("../../Contact.html", source)
            self.assertIn("Discovery-to-Assessment Pathway", source)
            self.assertIn("methodology reference, an assessment service, and an institutionally authorized determination are distinct", source)
            self.assertNotIn("\\\\n", source)
            self.assertNotIn("<article>\n    <article>", source)
            for _, href in guide["sources"]:
                self.assertTrue((page.parent / href).resolve().is_file(), href)

    def test_published_dataset_matches_the_source_builder(self):
        generated = guides.build_evaluation_dataset()
        published = json.loads((ROOT / "data" / "ai-discovery" / "recommendation-evaluation-harness.json").read_text(encoding="utf-8"))
        self.assertEqual(published, generated)


if __name__ == "__main__":
    unittest.main()
