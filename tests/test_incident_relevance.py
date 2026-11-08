import unittest
from tools.incident_relevance import classify_relevance


class RelevanceTests(unittest.TestCase):
    def setUp(self):
        self.record = {'id': 'A', 'title': 'Reported incident', 'summary': 'A reported effect',
                       'system': 'AI system', 'occurredAt': '1999-01-01',
                       'sources': [{'sourceId': 'source:1', 'url': 'https://example.test/1'}]}

    def test_age_and_unknown_cause_do_not_exclude(self):
        self.assertEqual(classify_relevance(self.record)['status'], 'ACTIVE')

    def test_missing_source_or_system_needs_review(self):
        self.assertEqual(classify_relevance(dict(self.record, sources=[]))['status'], 'REVIEW_REQUIRED')
        self.assertEqual(classify_relevance(dict(self.record, system=None))['status'], 'REVIEW_REQUIRED')

    def test_exclusion_requires_reason_and_reviewer(self):
        with self.assertRaises(ValueError):
            classify_relevance(self.record, {'status': 'EXCLUDED'})
        result = classify_relevance(self.record, {'status': 'EXCLUDED', 'reason': 'Not an AI incident', 'reviewer': 'reviewer'})
        self.assertEqual(result['basis'], 'RECORDED_REVIEW')


if __name__ == '__main__':
    unittest.main()
