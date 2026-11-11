import json
import unittest
from pathlib import Path

from tools.incident_analysis_storage import read_assessments

ROOT = Path(__file__).resolve().parents[1]


class RealIncidentRecognitionTests(unittest.TestCase):
    def test_real_incident_safety_invariants_without_claiming_accuracy(self):
        fixture = json.loads((ROOT / 'tests/fixtures/incident-recognition-v1.json').read_text(encoding='utf-8'))
        self.assertEqual(fixture['reviewStatus'], 'NOT_INDEPENDENTLY_REVIEWED')
        records = json.loads((ROOT / 'data/ai-incidents/incident-store.json').read_text(encoding='utf-8'))['incidents']
        ids = {record['id'] for record in records}
        store = read_assessments(ROOT / 'data/ai-incidents/analysis-store.json')
        latest = {}
        for item in store['assessments']:
            previous = latest.get(item['incidentId'])
            if previous is None or item['analysisVersion'] > previous['analysisVersion']:
                latest[item['incidentId']] = item
        for case in fixture['cases']:
            with self.subTest(incident=case['incidentId']):
                self.assertIn(case['incidentId'], ids)
                assessment = latest[case['incidentId']]
                self.assertFalse(assessment['oofApproved'])
                self.assertEqual(assessment['humanReview']['status'], 'Not performed')
                self.assertEqual(assessment['systemFailureClassification']['technicalMechanismStatus'], 'NOT_CONFIRMED')
                self.assertTrue(assessment['uncertainties'])


if __name__ == '__main__':
    unittest.main()
