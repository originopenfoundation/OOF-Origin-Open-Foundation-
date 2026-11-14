import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import avid_reference_source as avid


class AVIDReferenceTests(unittest.TestCase):
    def test_advisory_is_internal_and_not_independent_corroboration(self):
        sha = 'a' * 40
        path = 'reports/2026/AVID-2026-R1234.json'
        def fetch(url):
            if '?path=reports' in url:
                return [{'sha': sha}]
            if '/commits/' in url:
                return {'files': [{'filename': path, 'status': 'added'}]}
            return {'metadata': {'report_id': 'AVID-2026-R1234'}, 'problemtype': {'type': 'Advisory'}}
        result = avid.discover(fetch=fetch)
        reference = result['references'][0]
        self.assertEqual(reference['type'], 'Advisory')
        self.assertEqual(reference['disposition'], 'INTERNAL_REFERENCE')
        self.assertFalse(reference['independentCorroboration'])

    def test_rejects_mismatched_identifier(self):
        sha = 'b' * 40
        def fetch(url):
            if '?path=reports' in url:
                return [{'sha': sha}]
            if '/commits/' in url:
                return {'files': [{'filename': 'reports/2026/AVID-2026-R1234.json', 'status': 'added'}]}
            return {'metadata': {'report_id': 'other'}}
        with self.assertRaises(ValueError):
            avid.discover(fetch=fetch)


if __name__ == '__main__':
    unittest.main()
