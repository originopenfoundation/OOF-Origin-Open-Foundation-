'use strict';

const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const net = require('node:net');
const path = require('node:path');
const test = require('node:test');

const ROOT = path.resolve(__dirname, '../..');
const ORIGIN = 'https://originopenfoundation.org';

async function reservePort() {
  const listener = net.createServer();
  await new Promise((resolve, reject) => {
    listener.once('error', reject);
    listener.listen(0, '127.0.0.1', resolve);
  });
  const { port } = listener.address();
  await new Promise(resolve => listener.close(resolve));
  return port;
}

async function waitForServer(baseUrl, output) {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      const response = await fetch(`${baseUrl}/_lara/status`);
      if (response.ok) return;
    } catch {}
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error(`LaRA did not start. Output:\n${output()}`);
}

function assertSecurityHeaders(response) {
  assert.equal(response.headers.get('x-content-type-options'), 'nosniff');
  assert.equal(response.headers.get('x-frame-options'), 'DENY');
  assert.match(response.headers.get('content-security-policy') || '', /frame-ancestors 'none'/);
  assert.equal(response.headers.get('strict-transport-security'), 'max-age=31536000');
}

test('LaRA protects dynamic routes without preventing public discovery', async t => {
  const port = await reservePort();
  const baseUrl = `http://127.0.0.1:${port}`;
  let output = '';
  const server = spawn(process.execPath, ['lara/server.js'], {
    cwd: ROOT,
    env: {
      ...process.env,
      HOST: '127.0.0.1',
      PORT: String(port),
      NODE_ENV: 'production',
      LLM_PROVIDER: 'none',
      LARA_TRUST_PROXY: 'true',
      LARA_RATE_LIMIT_PER_MINUTE: '1',
      LARA_CHAT_CONCURRENCY: '1',
      LARA_REQUEST_TIMEOUT_MS: '15000',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const capture = chunk => { output += chunk.toString(); };
  server.stdout.on('data', capture);
  server.stderr.on('data', capture);
  t.after(() => {
    if (!server.killed) server.kill('SIGTERM');
  });

  await waitForServer(baseUrl, () => output);

  for (const route of ['/robots.txt', '/sitemap.xml', '/content/a/aga-about.html']) {
    const response = await fetch(`${baseUrl}${route}`);
    assert.equal(response.status, 200, route);
    assertSecurityHeaders(response);
  }

  const admin = await fetch(`${baseUrl}/_lara/admin/status`);
  assert.equal(admin.status, 401);
  assertSecurityHeaders(admin);

  const malformed = await fetch(`${baseUrl}/_lara/chat`, {
    method: 'POST',
    headers: { Origin: ORIGIN, 'Content-Type': 'application/json', 'X-Forwarded-For': '198.51.100.11' },
    body: '{',
  });
  assert.equal(malformed.status, 400);
  assertSecurityHeaders(malformed);

  const requestChat = async address => fetch(`${baseUrl}/_lara/chat`, {
    method: 'POST',
    headers: { Origin: ORIGIN, 'Content-Type': 'application/json', 'X-Forwarded-For': address },
    body: JSON.stringify({ question: 'Where can I find the OOF governance architecture?' }),
  });
  const firstVisitor = await requestChat('198.51.100.21');
  assert.equal(firstVisitor.status, 200);
  assertSecurityHeaders(firstVisitor);

  const limitedVisitor = await requestChat('198.51.100.21');
  assert.equal(limitedVisitor.status, 429);
  assert.equal(limitedVisitor.headers.get('retry-after'), '60');
  assertSecurityHeaders(limitedVisitor);

  const independentVisitor = await requestChat('198.51.100.22');
  assert.equal(independentVisitor.status, 200);

  const tooLarge = await fetch(`${baseUrl}/_lara/chat`, {
    method: 'POST',
    headers: { Origin: ORIGIN, 'Content-Type': 'application/json', 'X-Forwarded-For': '198.51.100.23' },
    body: JSON.stringify({ question: 'x'.repeat(12_001) }),
  });
  assert.equal(tooLarge.status, 413);
  assertSecurityHeaders(tooLarge);
});
