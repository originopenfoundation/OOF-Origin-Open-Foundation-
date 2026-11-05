import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from validate_json_schema import validate_instance


class EvidenceContractTests(unittest.TestCase):
    def test_engine_output_matches_versioned_schema(self):
        script = "const v=require('./lib/oof-evidence-verification').createVerifier({objects:[],resources:[],relationships:[]});console.log(JSON.stringify(v.assess({text:'A synthetic agent acted.'})))"
        value = json.loads(subprocess.check_output(['node', '-e', script], cwd=ROOT, text=True, encoding='utf-8'))
        path = ROOT / 'schemas/oof-evidence-verification.v1.schema.json'
        schema = json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(validate_instance(value, schema, path), [])
        value['claims'][0]['status'] = 'APPROVED'
        self.assertTrue(validate_instance(value, schema, path))
        value['claims'][0]['status'] = 'UNRESOLVED'
        value['verification_plans'][0]['execution_status'] = 'EXECUTED'
        self.assertTrue(validate_instance(value, schema, path))
