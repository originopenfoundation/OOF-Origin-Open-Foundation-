'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');

test('independent collector only accepts bounded categorical data from allowed origins', async () => {
  const { createCollector } = await import('../../supabase/functions/oof-analytics/core.mjs');
  const recorded = [];
  const collector = createCollector({ storage: { record: async value => recorded.push(value) },
    catalog: async () => new Map([['GOA', 'architecture']]) });
  const event = { event: 'page_view', content: 'architecture', contentId: 'GOA', source: 'google', language: 'en' };
  const send = (body, origin = 'https://originopenfoundation.org') => collector(new Request('https://example.org/event', {
    method: 'POST', headers: { origin, 'content-type': 'application/json' }, body: typeof body === 'string' ? body : JSON.stringify(body),
  }));
  const ok = await send(event);
  assert.equal(ok.status, 202);
  assert.equal(ok.headers.get('set-cookie'), null);
  assert.deepEqual(recorded, [event]);
  assert.equal((await send({ ...event, query: 'private text' })).status, 400);
  assert.equal((await send({ ...event, contentId: 'invented' })).status, 400);
  assert.equal((await send(event, 'https://evil.example')).status, 403);
  assert.equal((await send('{'.repeat(1100))).status, 400);
  assert.equal((await send('{')).status, 400);
  const protectedCollector = createCollector({ storage: { record: async value => recorded.push(value) },
    catalog: async () => new Map([['GOA', 'architecture']]), authorize: async () => false });
  assert.equal((await protectedCollector(new Request('https://example.org/event', { method: 'POST',
    headers: { origin: 'https://originopenfoundation.org', 'content-type': 'application/json' }, body: JSON.stringify(event) }))).status, 403);
  const unavailable = createCollector({ storage: { record: async () => { throw Error('offline'); } }, catalog: async () => new Map() });
  assert.equal((await unavailable(new Request('https://example.org/event', { method: 'POST',
    headers: { origin: 'https://originopenfoundation.org', 'content-type': 'application/json' },
    body: JSON.stringify({ ...event, contentId: undefined }) }))).status, 503);
});
