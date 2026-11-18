'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');

test('analytics proxy forwards only the bounded event and its own authorization', async () => {
  const { createHandler } = await import('../../workers/analytics-proxy/index.mjs');
  let forwarded;
  const handle = createHandler(async (url, options) => { forwarded = { url, options }; return new Response(null, { status: 202, headers: { 'Set-Cookie': 'bad=1' } }); });
  const make = (origin = 'https://originopenfoundation.org', body = '{}') => new Request('https://originopenfoundation.org/_oof/analytics/event', {
    method: 'POST', headers: { origin, 'content-type': 'application/json', cookie: 'private=1', 'x-oof-proxy-token': 'attacker', 'cf-connecting-ip': '192.0.2.1' }, body,
  });
  let limiterKey;
  const env = { OOF_ANALYTICS_PROXY_TOKEN: 'x'.repeat(48), ANALYTICS_RATE_LIMIT: { async limit({ key }) { limiterKey = key; return { success: true }; } } };
  const result = await handle(make(), env);
  assert.equal(result.status, 202);
  assert.equal(result.headers.get('set-cookie'), null);
  assert.equal(forwarded.options.headers['X-OOF-Proxy-Token'], env.OOF_ANALYTICS_PROXY_TOKEN);
  assert.equal(forwarded.options.redirect, 'manual');
  assert.equal(forwarded.options.headers.cookie, undefined);
  assert.match(limiterKey, /^[a-f0-9]{64}$/);
  assert.notEqual(limiterKey, '192.0.2.1');
  assert.equal((await handle(make('https://evil.example'), env)).status, 403);
  assert.equal((await handle(make(undefined, 'x'.repeat(1025)), env)).status, 413);
  assert.equal((await handle(make(), {})).status, 503);
  assert.equal((await handle(make(), { ...env, ANALYTICS_RATE_LIMIT: { async limit() { return { success: false }; } } })).status, 429);
  assert.equal((await handle(make(), { ...env, ANALYTICS_RATE_LIMIT: undefined })).status, 503);
});

test('proxy never forwards its secret through an upstream redirect', async () => {
  const { createHandler } = await import('../../workers/analytics-proxy/index.mjs');
  const handle = createHandler(async () => new Response(null, { status: 302, headers: { Location: 'https://attacker.example/' } }));
  const request = new Request('https://originopenfoundation.org/_oof/analytics/event', {
    method: 'POST', headers: { origin: 'https://originopenfoundation.org', 'content-type': 'application/json', 'cf-connecting-ip': '192.0.2.1' }, body: '{}',
  });
  const result = await handle(request, { OOF_ANALYTICS_PROXY_TOKEN: 'x'.repeat(48), ANALYTICS_RATE_LIMIT: { async limit() { return { success: true }; } } });
  assert.equal(result.status, 503);
  assert.equal(result.headers.get('location'), null);
});

test('standalone endpoint only allows the website origin and never allows credentialed CORS', async () => {
  const { createHandler } = await import('../../workers/analytics-proxy/index.mjs');
  const handle = createHandler(async () => new Response(null, { status: 202 }));
  const endpoint = 'https://oof-analytics-ingress.samuel-malicky2.workers.dev/_oof/analytics/event';
  const request = origin => new Request(endpoint, { method: 'OPTIONS', headers: { origin, 'access-control-request-method': 'POST' } });
  const ok = await handle(request('https://originopenfoundation.org'), {});
  assert.equal(ok.status, 204);
  assert.equal(ok.headers.get('access-control-allow-origin'), 'https://originopenfoundation.org');
  assert.equal(ok.headers.get('access-control-allow-credentials'), null);
  const blocked = await handle(request('https://attacker.example'), {});
  assert.equal(blocked.status, 403);
  assert.equal(blocked.headers.get('access-control-allow-origin'), null);
});

test('health check is rate limited and does not forward a body', async () => {
  const { createHandler } = await import('../../workers/analytics-proxy/index.mjs');
  let forwarded;
  const handle = createHandler(async (url, options) => { forwarded = options; return new Response(null, { status: 204 }); });
  const request = new Request('https://oof-analytics-ingress.samuel-malicky2.workers.dev/_oof/analytics/event', { method: 'HEAD', headers: { origin: 'https://originopenfoundation.org', 'cf-connecting-ip': '192.0.2.1' } });
  const env = { OOF_ANALYTICS_PROXY_TOKEN: 'x'.repeat(48), ANALYTICS_RATE_LIMIT: { async limit() { return { success: true }; } } };
  assert.equal((await handle(request, env)).status, 204);
  assert.equal(forwarded.method, 'HEAD');
  assert.equal(forwarded.body, undefined);
  assert.equal(forwarded.redirect, 'manual');
});
