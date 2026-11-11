import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.audit_incident_storage_capacity import inventory
from tools.stage_incident_storage_migration import stage
from tools.incident_analysis_storage import read_assessments, write_assessments, recover_interrupted_write
from tools.incident_relevance import record_review


class StorageInventoryTests(unittest.TestCase):
    def test_inventory_preserves_versions_and_detects_invalid_links(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            store = directory / 'analysis.json'
            incidents = directory / 'incidents.json'
            items = [
                {'incidentId': 'A', 'analysisVersion': 1, 'assessmentIdentity': 'a1'},
                {'incidentId': 'A', 'analysisVersion': 2, 'assessmentIdentity': 'a2', 'supersedes': 'a1'},
                {'incidentId': 'B', 'analysisVersion': 1, 'assessmentIdentity': 'b1', 'supersedes': 'missing'},
            ]
            store.write_text(json.dumps({'assessments': items}), encoding='utf-8')
            incidents.write_text(json.dumps({'incidents': [{'id': 'A'}]}), encoding='utf-8')
            original = store.read_bytes()
            result = inventory(store, incidents)
            self.assertEqual(result['activeAssessmentCount'], 2)
            self.assertEqual(result['historicalAssessmentCount'], 1)
            self.assertEqual(result['unknownIncidentIds'], ['B'])
            self.assertEqual(result['missingSupersedes'], ['missing'])
            self.assertEqual(result['status'], 'INVENTORY_ONLY_NOT_MIGRATED')
            self.assertEqual(store.read_bytes(), original)

    def test_inventory_detects_duplicate_ids_and_versions(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            store, incidents = directory / 'a.json', directory / 'i.json'
            item = {'incidentId': 'A', 'analysisVersion': 1, 'assessmentIdentity': 'a1'}
            store.write_text(json.dumps({'assessments': [item, item]}), encoding='utf-8')
            incidents.write_text(json.dumps({'incidents': [{'id': 'A'}]}), encoding='utf-8')
            result = inventory(store, incidents)
            self.assertEqual(result['duplicateAssessmentIds'], ['a1'])
            self.assertEqual(result['duplicateIncidentVersions'], [['A', 1]])

    def test_stage_reconciles_and_backs_up_without_modifying_original(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            store, incidents = directory / 'a.json', directory / 'i.json'
            items = [
                {'incidentId': 'A', 'analysisVersion': 1, 'assessmentIdentity': 'a1'},
                {'incidentId': 'A', 'analysisVersion': 2, 'assessmentIdentity': 'a2', 'supersedes': 'a1'},
            ]
            store.write_text(json.dumps({'assessments': items}), encoding='utf-8')
            incidents.write_text(json.dumps({'incidents': [{'id': 'A'}]}), encoding='utf-8')
            before = store.read_bytes()
            out = directory / 'staged'
            result = stage(out, store, incidents)
            self.assertEqual(result['verifiedAssessmentCount'], 2)
            self.assertEqual((out / 'analysis-store.backup.json').read_bytes(), before)
            self.assertEqual(store.read_bytes(), before)
            self.assertEqual(json.loads((out / 'active-intelligence.json').read_text())['assessments'][0]['assessmentIdentity'], 'a2')
            self.assertEqual(json.loads((out / 'historical-archive.json').read_text())['assessments'][0]['assessmentIdentity'], 'a1')
            legacy = out / 'analysis-store.json'
            combined = read_assessments(legacy)
            self.assertEqual({item['assessmentIdentity'] for item in combined['assessments']}, {'a1', 'a2'})
            combined['assessments'].append({'incidentId': 'A', 'analysisVersion': 3, 'assessmentIdentity': 'a3', 'supersedes': 'a2'})
            write_assessments(legacy, combined)
            self.assertEqual(len(read_assessments(legacy)['assessments']), 3)
            self.assertEqual(json.loads((out / 'active-intelligence.json').read_text())['assessments'][0]['assessmentIdentity'], 'a3')
            combined = read_assessments(legacy)
            record_review(combined, 'A', {'status': 'EXCLUDED', 'reason': 'reviewed', 'reviewer': 'reviewer', 'reviewedAt': '2026-11-08T10:00:00Z'})
            write_assessments(legacy, combined)
            self.assertEqual(json.loads((out / 'active-intelligence.json').read_text())['assessments'], [])
            self.assertEqual(len(json.loads((out / 'historical-archive.json').read_text())['assessments']), 3)
            combined = read_assessments(legacy)
            record_review(combined, 'A', {'status': 'ACTIVE', 'reason': 'restored', 'reviewer': 'reviewer', 'reviewedAt': '2026-11-08T11:00:00Z'})
            write_assessments(legacy, combined)
            self.assertEqual(json.loads((out / 'active-intelligence.json').read_text())['assessments'][0]['assessmentIdentity'], 'a3')
            self.assertEqual(len(read_assessments(legacy)['relevanceHistory']), 2)
            (out / 'historical-archive.json').write_text('{}', encoding='utf-8')
            with self.assertRaises(ValueError):
                read_assessments(legacy)
            with self.assertRaises(ValueError):
                stage(out, store, incidents)

    def test_stage_refuses_invalid_references_without_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            store, incidents = directory / 'a.json', directory / 'i.json'
            store.write_text(json.dumps({'assessments': [{'incidentId': 'A', 'analysisVersion': 1, 'assessmentIdentity': 'a1', 'supersedes': 'missing'}]}))
            incidents.write_text(json.dumps({'incidents': [{'id': 'A'}]}))
            with self.assertRaises(ValueError):
                stage(directory / 'staged', store, incidents)
            self.assertFalse((directory / 'staged').exists())

    def test_recover_interrupted_pair_update(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            store, incidents = directory / 'a.json', directory / 'i.json'
            item = {'incidentId': 'A', 'analysisVersion': 1, 'assessmentIdentity': 'a1'}
            store.write_text(json.dumps({'assessments': [item]}), encoding='utf-8')
            incidents.write_text(json.dumps({'incidents': [{'id': 'A'}]}), encoding='utf-8')
            out = directory / 'staged'
            stage(out, store, incidents)
            recovery = out / '.incident-analysis-recovery'
            recovery.mkdir()
            shutil.copy2(out / 'active-intelligence.json', recovery / 'active.old')
            shutil.copy2(out / 'historical-archive.json', recovery / 'archive.old')
            (out / 'historical-archive.json').write_text('{}', encoding='utf-8')
            with self.assertRaises(ValueError):
                read_assessments(out / 'analysis-store.json')
            self.assertTrue(recover_interrupted_write(out / 'analysis-store.json'))
            self.assertEqual(len(read_assessments(out / 'analysis-store.json')['assessments']), 1)
            self.assertFalse(recovery.exists())


if __name__ == '__main__':
    unittest.main()
