import json
import subprocess
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from validate_json_schema import validate_instance


class CrossArchitectureContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        script = "const k=require('./lara/knowledge').readShared(process.cwd());const c=require('./lib/oof-capabilities/adapters').createCapabilities(k);const d=require('./lib/oof-discovery').discover({text:'AI agent unauthorized payment with unknown identity'});console.log(JSON.stringify({reasoning:require('./lib/oof-cross-architecture-reasoning').reason(k,{problem:d.result}),capabilities:c.definitions()}));"
        cls.output = json.loads(subprocess.check_output(['node', '-e', script], cwd=ROOT, text=True, encoding='utf-8'))

    def test_reasoning_matches_versioned_schema(self):
        schema = json.loads((ROOT / 'schemas/oof-cross-architecture.v1.schema.json').read_text(encoding='utf-8'))
        self.assertEqual(validate_instance(self.output['reasoning'], schema, ROOT / 'schemas/oof-cross-architecture.v1.schema.json'), [])

    def test_four_capabilities_match_versioned_definition(self):
        schema = json.loads((ROOT / 'schemas/oof-capability.v1.schema.json').read_text(encoding='utf-8'))
        self.assertEqual(len(self.output['capabilities']), 4)
        for capability in self.output['capabilities']:
            self.assertEqual(validate_instance(capability, schema, ROOT / 'schemas/oof-capability.v1.schema.json'), [])
            self.assertEqual(capability['allowed_tools'], [])
            self.assertEqual(capability['execution_permissions'], ['knowledge:read'])

    def test_schema_rejects_missing_provenance_and_public_mode(self):
        schema = json.loads((ROOT / 'schemas/oof-cross-architecture.v1.schema.json').read_text(encoding='utf-8'))
        value = dict(self.output['reasoning'])
        value.pop('provenance')
        self.assertTrue(validate_instance(value, schema, ROOT / 'schemas/oof-cross-architecture.v1.schema.json'))
        value = {**self.output['reasoning'], 'report_only': False}
        self.assertTrue(validate_instance(value, schema, ROOT / 'schemas/oof-cross-architecture.v1.schema.json'))
