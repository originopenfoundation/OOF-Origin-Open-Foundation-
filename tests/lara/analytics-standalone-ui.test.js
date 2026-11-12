'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

test('admin invitation fragment is removed and no browser storage or request is used on load', () => {
  const source = fs.readFileSync(path.join(__dirname, '../../assets/js/analytics-admin-standalone.js'), 'utf8');
  const elements = new Map();
  const document = { querySelector(selector) {
    if (!elements.has(selector)) elements.set(selector, { hidden: false, addEventListener() {}, textContent: '' });
    return elements.get(selector);
  } };
  let cleanUrl, networkCalls = 0;
  const context = { document, URLSearchParams, location: { hash: '#access_token=sensitive-token&type=invite', pathname: '/analytics-admin/', search: '' },
    history: { replaceState(_a, _b, url) { cleanUrl = url; } }, fetch() { networkCalls++; },
    localStorage: new Proxy({}, { get() { throw Error('persistent storage accessed'); } }),
    sessionStorage: new Proxy({}, { get() { throw Error('session storage accessed'); } }) };
  vm.runInNewContext(source, context);
  assert.equal(cleanUrl, '/analytics-admin/');
  assert.equal(elements.get('#setup').hidden, false);
  assert.equal(elements.get('#login').hidden, true);
  assert.equal(networkCalls, 0);
});
