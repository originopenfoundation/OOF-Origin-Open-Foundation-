'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');

test('independent admin checks authorization, limits requests and distinguishes unavailable data', async () => {
  const { createAdminHandler } = await import('../../supabase/functions/oof-analytics-admin/core.mjs');
  const handler = createAdminHandler({ authenticate: async token => token === 'valid-token',
    report: async () => ({ status: 'AVAILABLE', totals: [{ event: 'page_view', count: 3 }] }),
    cloudflare: async () => { throw new Error('not configured'); } });
  const call = (url, headers = {}) => handler(new Request(url, { headers }));
  const base = 'https://example.org/admin';
  assert.equal((await call(base)).status, 401);
  assert.equal((await call(base, { authorization: 'Bearer wrong' })).status, 401);
  assert.equal((await call(base, { authorization: 'Bearer valid-token', origin: 'https://evil.example' })).status, 403);
  assert.equal((await call(base + '?days=365', { authorization: 'Bearer valid-token' })).status, 400);
  assert.equal((await call(base + '?days=7&foo=1', { authorization: 'Bearer valid-token' })).status, 400);
  const response = await call(base + '?days=7', { authorization: 'Bearer valid-token', origin: 'https://originopenfoundation.org' });
  const data = await response.json();
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('cache-control'), 'no-store');
  assert.equal(response.headers.get('set-cookie'), null);
  assert.equal(data.independent.totals[0].count, 3);
  assert.equal(data.cloudflare.status, 'UNAVAILABLE');
  assert.equal(data.cloudflare.rows, null);
  assert.equal(JSON.stringify(data).includes('valid-token'), false);
});
