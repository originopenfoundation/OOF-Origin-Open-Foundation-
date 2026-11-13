'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { approvedScopes } = require('../../lara/knowledge/communication-approval');
const digest = crypto.createHash('sha256').update(fs.readFileSync(
  path.join(__dirname, '../../lara/knowledge/public-communication-policy.json')
)).digest('hex');

function record(approval = {}, object = {}) {
  return {
    id: 'OOF-KO-LARA-PUBLIC-COMMUNICATION', status: 'active',
    visibility: 'public', authorityState: 'CANONICAL_AUTHORITATIVE', allowedConsumers: ['LaRA'],
    sourceAuthority: {
      domains: ['publicCommunicationApproval'],
      publicCommunicationApproval: {status: 'approved', policyDigest: digest, scopes: ['conversation'], ...approval},
    },
    ...object,
  };
}

test('rejects malformed, unauthorized, expired and superseded approvals', () => {
  const now = Date.parse('2026-11-14T00:00:00Z');
  for (const candidate of [
    record({ expiresAt: '2026-11-14T00:00:00Z' }),
    record({ expiresAt: 'invalid' }),
    record({}, { supersededBy: 'newer' }),
    record({}, { allowedConsumers: 'LaRA' }),
    record({ scopes: 'conversation' }),
    record({ policyDigest: 'wrong' }),
  ]) assert.deepEqual(approvedScopes({objects: [candidate]}, now), []);
  assert.deepEqual(approvedScopes({objects: [record(), record()]}, now), []);
  assert.deepEqual(approvedScopes({objects: [record({expiresAt: '2027-01-01T00:00:00Z'})]}, now), ['conversation']);
});
