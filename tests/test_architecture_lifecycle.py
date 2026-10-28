import sys
import unittest
import json
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from build_knowledge_infrastructure import cross_validate_architecture


class LifecycleTests(unittest.TestCase):
    def architecture(self, status='completed', acronym='EXAMPLE'):
        return {'acronym': acronym, 'status': status, 'primaryPage': {'url': 'example.html'}, 'standards': []}

    def test_explicit_pending_is_nonblocking_without_approval(self):
        for status in ('discovered', 'draft', 'in-progress', 'pending', 'published'):
            result = cross_validate_architecture(None, self.architecture(status), False)
            self.assertEqual(result['result'], 'PENDING')
            self.assertFalse(result['approvalVerified'])
            self.assertEqual(result['authorityState'], 'SUPPORTING_CITABLE')

    def test_false_canonical_claim_blocks(self):
        item = self.architecture()
        self.assertEqual(cross_validate_architecture(item, item, False)['result'], 'CONFLICT')

    def test_current_authorized_agreement_passes(self):
        for status in ('completed', 'published'):
            item = self.architecture(status)
            self.assertEqual(cross_validate_architecture(item, item, True)['result'], 'PASS')

    def test_withdrawn_or_superseded_cannot_remain_canonical(self):
        for status in ('withdrawn', 'superseded'):
            item = self.architecture(status)
            self.assertEqual(cross_validate_architecture(item, item, True)['result'], 'CONFLICT')

    def test_unknown_is_not_pending_or_canonical(self):
        item = self.architecture('unknown')
        self.assertEqual(cross_validate_architecture(None, item, False)['result'], 'CONFLICT')
        self.assertEqual(cross_validate_architecture(item, item, True)['result'], 'CONFLICT')

    def test_unrelated_identity_conflict_remains_blocking(self):
        self.assertEqual(cross_validate_architecture(self.architecture(), self.architecture(acronym='OTHER'), True)['result'], 'CONFLICT')

    def test_draft_in_approved_registry_is_a_conflict(self):
        item = self.architecture('draft')
        self.assertEqual(cross_validate_architecture(item, item, True)['result'], 'CONFLICT')

    def test_generated_slga_is_traceable_without_approved_membership(self):
        root = Path(__file__).resolve().parents[1]
        approved = json.loads((root / 'data/oof-architecture-map-approved.json').read_text(encoding='utf-8'))
        self.assertNotIn('SLGA', approved['approved'])
        objects = json.loads((root / 'data/knowledge/objects-core.json').read_text(encoding='utf-8'))['objects']
        slga = next(item for item in objects if item['id'] == 'OOF-KO-ARCH-SLGA')
        self.assertEqual(slga['status'], 'in-progress')
        self.assertEqual(slga['authorityState'], 'SUPPORTING_CITABLE')
        self.assertFalse(slga['sourceAuthority']['approvalVerified'])
        self.assertTrue(slga['provenance']['contentHash'])

    def test_generated_drafts_never_enter_canonical_retrieval(self):
        root = Path(__file__).resolve().parents[1]
        objects = json.loads((root / 'data/knowledge/objects-core.json').read_text(encoding='utf-8'))['objects']
        drafts = [item for item in objects if re.search(r'draft|pending|in.progress|development|incomplete', item.get('status', ''), re.I)]
        self.assertTrue(drafts)
        self.assertTrue(all(item['authorityState'] != 'CANONICAL_AUTHORITATIVE' for item in drafts))
