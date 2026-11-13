'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const policyFile = path.join(__dirname, 'public-communication-policy.json');
const statuses = new Set(['current', 'active', 'published']);

function approvedScopes(index, now = Date.now()) {
  const raw = fs.readFileSync(policyFile);
  const policy = JSON.parse(raw);
  if (!Array.isArray(index?.objects)) return [];
  const candidates = index.objects.filter(object => object?.id === policy.approval_object_id);
  if (candidates.length !== 1) return [];

  const object = candidates[0];
  const authority = object.sourceAuthority;
  const approval = authority?.publicCommunicationApproval;
  if (object.authorityState !== 'CANONICAL_AUTHORITATIVE' || object.visibility !== 'public' ||
      !statuses.has(object.status) || !Array.isArray(object.allowedConsumers) ||
      !object.allowedConsumers.includes('LaRA') || !Array.isArray(authority?.domains) ||
      !authority.domains.includes('publicCommunicationApproval') || approval?.status !== 'approved' ||
      approval.policyDigest !== crypto.createHash('sha256').update(raw).digest('hex') ||
      !Array.isArray(approval.scopes)) return [];

  for (const record of [object, approval]) {
    if (record.supersededBy != null) return [];
    if (Object.hasOwn(record, 'expiresAt')) {
      const expiry = typeof record.expiresAt === 'string' ? Date.parse(record.expiresAt) : NaN;
      if (!Number.isFinite(expiry) || expiry <= now) return [];
    }
  }

  return [...new Set(approval.scopes.filter(scope => policy.allowed_scopes.includes(scope)))];
}

module.exports = { approvedScopes };
