'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');

test('analytics proxy forwards only the bounded event and its own authorization', async () => {
  const { createHandler } = await import('../../workers/analytics-proxy/index.mjs');
  let forwarded;
  const handle = createHandler(async (url, options) => { forwarded = { url, options }; return new Response(null, { status: 202, headers: { 'Set-Cookie': 'bad=1' } }); });
  const make = (origin = 'https://originopenfoundation.org', body = '{}') => new Request('https://originopenfoundation.org/_oof/analytics/event', {
    method: 'POST', headers: { origin, 'content-type': 'application/json', cookie: 'private=1', 'x-oof-proxy-token': 'attacker' }, body,
  });
  const env = { OOF_ANALYTICS_PROXY_TOKEN: 'x'.repeat(48) };
  const result = await handle(make(), env);
  assert.equal(result.status, 202);
  assert.equal(result.headers.get('set-cookie'), null);
  assert.equal(forwarded.options.headers['X-OOF-Proxy-Token'], env.OOF_ANALYTICS_PROXY_TOKEN);
  assert.equal(forwarded.options.headers.cookie, undefined);
  assert.equal((await handle(make('https://evil.example'), env)).status, 403);
  assert.equal((await handle(make(undefined, 'x'.repeat(1025)), env)).status, 413);
  assert.equal((await handle(make(), {})).status, 503);
});
