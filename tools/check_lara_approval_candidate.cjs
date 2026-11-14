'use strict';
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const policyBytes = fs.readFileSync(path.join(__dirname, '../lara/knowledge/public-communication-policy.json'));
const policy = JSON.parse(policyBytes);
const candidate = require('../lara/knowledge/public-communication-approval-candidate.json');
assert.equal(candidate.id, policy.approval_object_id);
assert.equal(candidate.policyVersion, policy.version);
assert.equal(candidate.policyDigest, crypto.createHash('sha256').update(policyBytes).digest('hex'));
assert.equal(candidate.status, 'pending_release_acceptance');
assert.ok(candidate.requestedScopes.length && candidate.requestedScopes.every(scope => policy.allowed_scopes.includes(scope)));
const { approvedScopes } = require('../lara/knowledge/communication-approval');
assert.deepEqual(approvedScopes({ objects: [candidate] }), [],
  'Pending release evidence must never grant a runtime scope');
console.log('LaRA approval candidate matches the communication policy.');
