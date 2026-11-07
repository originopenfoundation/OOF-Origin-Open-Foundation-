import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('historical_engine', ROOT / 'tools/incident_intelligence_v2.py')
engine = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(engine)


class HistoricalReferenceTests(unittest.TestCase):
    def setUp(self):
        self.source = {'id': 'standard', 'artifactType': 'ParentStandard', 'architectureId': 'architecture',
                       'canonicalName': 'Synthetic Draft', 'canonicalUrl': 'https://originopenfoundation.org/synthetic.html',
                       'authorityState': 'SUPPORTING_CITABLE', 'status': 'draft', 'provenance': {'contentHash': 'a' * 64}}
        self.reference = {'objectId': 'standard', 'artifactType': 'ParentStandard', 'name': 'Synthetic Draft',
                          'canonicalUrl': self.source['canonicalUrl'],
                          'canonicalProvenance': {'contentHash': 'a' * 64, 'knowledgeBuildId': 'OOF-KI-1.1-' + 'b' * 12}}
        self.knowledge = SimpleNamespace(objects={'architecture': {'id': 'architecture', 'artifactType': 'Architecture'}},
                                         source_objects={'standard': self.source})

    def assessment(self, version, references):
        return {'assessmentIdentity': 'synthetic-v' + str(version), 'incidentId': 'synthetic', 'analysisVersion': version,
                'engineVersion': 'historical-fixture', 'analysisType': 'Automated', 'oofApproved': False,
                'humanReview': {'status': 'Not performed'}, 'architectureAnalysis': {'primaryArchitecture': {
                    'objectId': 'architecture', 'reasonForRelevance': 'Synthetic archived source context',
                    'supportingEvidence': ['synthetic-record'], 'relevantStandardsModules': references},
                    'contributingArchitectures': []}}

    def validate(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); analysis = root / 'analysis.json'; store = root / 'incidents.json'
            analysis.write_text(json.dumps({'assessments': rows}), encoding='utf-8')
            store.write_text(json.dumps({'incidents': [{'id': 'synthetic'}]}), encoding='utf-8')
            before = analysis.read_bytes(); reviews = []
            with patch.object(engine, 'KnowledgeLayer', return_value=self.knowledge):
                errors = engine.validate(analysis, store, historical_reviews=reviews)
            self.assertEqual(before, analysis.read_bytes())
            return errors, reviews

    def test_superseded_traceable_draft_is_retained_as_unverified_history(self):
        errors, reviews = self.validate([self.assessment(1, [self.reference]), self.assessment(2, [])])
        self.assertEqual(errors, [])
        self.assertEqual(len(reviews), 1)
        self.assertFalse(reviews[0]['currentCanonical'])
        self.assertFalse(reviews[0]['historicalAuthorityVerified'])
        self.assertEqual(reviews[0]['status'], 'ARCHIVED_REFERENCE_REQUIRES_REVIEW')
        self.assertNotIn('standard', self.knowledge.objects)

    def test_latest_draft_is_rejected_even_for_an_old_engine(self):
        errors, reviews = self.validate([self.assessment(1, []), self.assessment(2, [self.reference])])
        self.assertTrue(any('not canonical' in error for error in errors))
        self.assertEqual(reviews, [])

    def test_fabricated_or_mismatched_historical_source_is_rejected(self):
        for field, value in [('objectId', 'invented'), ('name', 'Approved'), ('canonicalUrl', 'https://example.test/fake')]:
            reference = {**self.reference, field: value}
            errors, reviews = self.validate([self.assessment(1, [reference]), self.assessment(2, [])])
            self.assertTrue(errors)
            self.assertEqual(reviews, [])

    def test_digest_and_build_identity_are_required(self):
        for field, value in [('contentHash', 'c' * 64), ('contentHash', ''), ('knowledgeBuildId', 'invented')]:
            reference = copy.deepcopy(self.reference); reference['canonicalProvenance'][field] = value
            self.assertIsNone(engine.archived_reference_review(reference, 'architecture', self.knowledge))

    def test_architecture_ownership_is_not_relaxed(self):
        self.assertIsNone(engine.archived_reference_review(self.reference, 'other-architecture', self.knowledge))


if __name__ == '__main__':
    unittest.main()
