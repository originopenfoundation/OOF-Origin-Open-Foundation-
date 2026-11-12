'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const tracker = fs.readFileSync(path.resolve(__dirname, '../../assets/js/oof-website-analytics.js'), 'utf8');

async function execute(config, referrer = 'https://www.google.com/search?q=private', catalog = null) {
  const calls = [], listeners = {};
  const context = { URL, Set, JSON, Element: class {}, location: { pathname: '/architecture.html', origin: 'https://originopenfoundation.org', hostname: 'originopenfoundation.org' },
    navigator: {}, document: { documentElement: { lang: 'en' }, referrer, addEventListener: (name, callback) => { listeners[name] = callback; } },
    fetch: async (url, options) => { calls.push({ url: String(url), options }); return url === '/assets/data/oof-analytics-config.json' ? { ok: true, json: async () => config } : url === '/assets/data/oof-analytics-catalog.json' && catalog ? { ok: true, json: async () => catalog } : { ok: false }; } };
  vm.runInNewContext(tracker, context);
  await new Promise(resolve => setImmediate(resolve));
  return { calls, listeners };
}

test('disabled tracker sends no event', async () => {
  const result = await execute({ enabled: false });
  assert.equal(result.calls.length, 1);
});

test('tracker sends only allowed categories without URLs, queries or credentials', async () => {
  const result = await execute({ enabled: true, endpoint: '/_oof/analytics/event' });
  assert.equal(result.calls.length, 4);
  for (const call of result.calls.filter(item => item.options?.method === 'POST')) {
    const body = JSON.parse(call.options.body);
    assert.equal(body.source, 'google');
    assert.deepEqual(Object.keys(body).sort(), ['content', 'event', 'language', 'source']);
    assert.ok(!call.options.body.includes('private'));
    assert.equal(call.options.credentials, 'omit');
    assert.equal(call.options.referrerPolicy, 'no-referrer');
  }
  result.listeners['oof:search-results']({ detail: { hasResults: false, query: 'secret password' } });
  assert.ok(!result.calls.at(-1).options.body.includes('secret'));
});

test('tracker refuses external collectors and does not misattribute deceptive hostnames', async () => {
  const external = await execute({ enabled: true, endpoint: 'https://example.com/_oof/analytics/event' });
  assert.equal(external.calls.length, 1);
  const spoofed = await execute({ enabled: true, endpoint: '/_oof/analytics/event' }, 'https://www.google.com.evil.example/path');
  assert.equal(JSON.parse(spoofed.calls.find(item => item.options?.method === 'POST').options.body).source, 'other_website');
});

test('known canonical pages send only their public canonical identity', async () => {
  const result = await execute({ enabled: true, endpoint: '/_oof/analytics/event' }, '',
    { '/architecture.html': { id: 'OOF-KO-ARCH-AGA', content: 'architecture' } });
  const body = JSON.parse(result.calls.find(item => item.options?.method === 'POST').options.body);
  assert.equal(body.contentId, 'OOF-KO-ARCH-AGA');
  assert.ok(!JSON.stringify(body).includes('/architecture.html'));
});
