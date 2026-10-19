'use strict';

const crypto = require('node:crypto');

function safeEqual(a, b) {
  const left = Buffer.from(String(a || ''));
  const right = Buffer.from(String(b || ''));
  return left.length === right.length && crypto.timingSafeEqual(left, right);
}

function parsePositiveInteger(value, fallback, minimum = 1, maximum = 1_000_000) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= minimum && parsed <= maximum ? parsed : fallback;
}

function clientAddress(req, { trustProxy = false } = {}) {
  if (trustProxy) {
    const forwarded = String(req.headers['x-forwarded-for'] || '')
      .split(',')
      .map(value => value.trim())
      .find(Boolean);
    if (forwarded) return forwarded.slice(0, 128);
  }
  return String(req.socket?.remoteAddress || 'unknown').replace(/^::ffff:/, '').slice(0, 128);
}

function rateLimiter(limit = 20, windowMs = 60_000, { maxEntries = 10_000 } = {}) {
  const entries = new Map();
  const safeLimit = parsePositiveInteger(limit, 20);
  const safeWindow = parsePositiveInteger(windowMs, 60_000, 1_000, 86_400_000);
  const safeMaxEntries = parsePositiveInteger(maxEntries, 10_000, 100, 100_000);

  function prune(now) {
    for (const [key, entry] of entries) {
      if (entry.resetAt <= now) entries.delete(key);
    }
    while (entries.size > safeMaxEntries) entries.delete(entries.keys().next().value);
  }

  function consume(key, now = Date.now()) {
    let entry = entries.get(key);
    if (!entry || entry.resetAt <= now) entry = { count: 0, resetAt: now + safeWindow };
    entry.count += 1;
    entries.set(key, entry);
    if (entries.size > safeMaxEntries) prune(now);
    return {
      allowed: entry.count <= safeLimit,
      remaining: Math.max(0, safeLimit - entry.count),
      retryAfterSeconds: Math.max(1, Math.ceil((entry.resetAt - now) / 1000)),
    };
  }

  consume.prune = () => prune(Date.now());
  return consume;
}

function concurrencyGate(limit = 4) {
  const safeLimit = parsePositiveInteger(limit, 4, 1, 100);
  let active = 0;
  return {
    tryAcquire() {
      if (active >= safeLimit) return null;
      active += 1;
      let released = false;
      return () => {
        if (!released) {
          released = true;
          active -= 1;
        }
      };
    },
    active: () => active,
  };
}

function applySecurityHeaders(res, { production = false } = {}) {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  res.setHeader('Permissions-Policy', 'accelerometer=(), camera=(), geolocation=(), microphone=(), payment=(), usb=()');
  res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');
  res.setHeader('Content-Security-Policy', "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'; object-src 'none'");
  if (production) res.setHeader('Strict-Transport-Security', 'max-age=31536000');
}

module.exports = { safeEqual, parsePositiveInteger, clientAddress, rateLimiter, concurrencyGate, applySecurityHeaders };
