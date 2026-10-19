'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const { applySecurityHeaders, clientAddress, concurrencyGate, rateLimiter } = require('../../lara/security');

function request(headers = {}, address = '203.0.113.10') {
  return { headers, socket: { remoteAddress: address } };
}

test('rate limiter returns a bounded retry window instead of blocking by user agent', () => {
  const limiter = rateLimiter(2, 1_000);
  assert.equal(limiter('chat:visitor', 0).allowed, true);
  assert.equal(limiter('chat:visitor', 1).allowed, true);
  const rejected = limiter('chat:visitor', 2);
  assert.equal(rejected.allowed, false);
  assert.equal(rejected.retryAfterSeconds, 1);
  assert.equal(limiter('chat:visitor', 1_001).allowed, true);
});

test('forwarded client addresses are used only for an explicitly trusted proxy', () => {
  const req = request({ 'x-forwarded-for': '198.51.100.8, 10.0.0.1' });
  assert.equal(clientAddress(req), '203.0.113.10');
  assert.equal(clientAddress(req, { trustProxy: true }), '198.51.100.8');
});

test('chat concurrency gate releases capacity exactly once', () => {
  const gate = concurrencyGate(1);
  const release = gate.tryAcquire();
  assert.equal(typeof release, 'function');
  assert.equal(gate.tryAcquire(), null);
  release();
  release();
  assert.equal(gate.active(), 0);
  assert.equal(typeof gate.tryAcquire(), 'function');
});

test('backend response headers deny embedding and unsafe content types', () => {
  const headers = new Map();
  const response = { setHeader: (name, value) => headers.set(name, value) };
  applySecurityHeaders(response, { production: true });
  assert.equal(headers.get('X-Content-Type-Options'), 'nosniff');
  assert.equal(headers.get('X-Frame-Options'), 'DENY');
  assert.match(headers.get('Content-Security-Policy'), /frame-ancestors 'none'/);
  assert.equal(headers.get('Strict-Transport-Security'), 'max-age=31536000');
});
