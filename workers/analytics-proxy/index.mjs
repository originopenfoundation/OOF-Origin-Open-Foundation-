const TARGET = 'https://zxpufntydcqktylzicky.supabase.co/functions/v1/oof-analytics';
const ORIGINS = new Set(['https://originopenfoundation.org', 'https://www.originopenfoundation.org']);
const ENDPOINT_ORIGINS = new Set([...ORIGINS, 'https://oof-analytics-ingress.samuel-malicky2.workers.dev']);

export function createHandler(fetchImpl = fetch) {
  return async (request, env) => {
    const url = new URL(request.url);
    const origin = request.headers.get('origin');
    const cors = ORIGINS.has(origin) ? { 'Access-Control-Allow-Origin': origin, Vary: 'Origin' } : {};
    const reply = status => new Response(null, { status, headers: { ...cors, 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' } });
    if (!ENDPOINT_ORIGINS.has(url.origin) || url.pathname !== '/_oof/analytics/event' || url.search || url.hash) return reply(404);
    if (!ORIGINS.has(origin)) return reply(403);
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: { ...cors, 'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Max-Age': '600', 'Cache-Control': 'no-store' } });
    if (!['POST', 'HEAD'].includes(request.method)) return reply(405);
    if (request.method === 'POST' && !/^application\/json(?:\s*;|$)/i.test(request.headers.get('content-type') || '')) return reply(415);
    if (typeof env.OOF_ANALYTICS_PROXY_TOKEN !== 'string' || env.OOF_ANALYTICS_PROXY_TOKEN.length < 43) return reply(503);
    if (!/^[\x21-\x7e]+$/.test(env.OOF_ANALYTICS_PROXY_TOKEN)) return reply(503);
    if (request.method === 'POST' && (!request.body || Number(request.headers.get('content-length') || 0) > 1024)) return reply(413);
    const clientIp = request.headers.get('cf-connecting-ip');
    if (!clientIp || !env.ANALYTICS_RATE_LIMIT || typeof env.ANALYTICS_RATE_LIMIT.limit !== 'function') return reply(503);
    try {
      const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(env.OOF_ANALYTICS_PROXY_TOKEN), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
      const minute = Math.floor(Date.now() / 60000);
      const digest = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(`${minute}:${clientIp}`));
      const pseudonymousKey = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
      if (!(await env.ANALYTICS_RATE_LIMIT.limit({ key: pseudonymousKey })).success) return reply(429);
    } catch { return reply(503); }
    if (request.method === 'HEAD') {
      try {
        const upstream = await fetchImpl(TARGET, { method: 'HEAD', redirect: 'manual',
          headers: { Origin: origin, 'X-OOF-Proxy-Token': env.OOF_ANALYTICS_PROXY_TOKEN } });
        return reply(upstream.status === 204 ? 204 : 503);
      } catch { return reply(503); }
    }
    const reader = request.body.getReader();
    const parts = []; let size = 0;
    for (;;) {
      const part = await reader.read();
      if (part.done) break;
      size += part.value.byteLength;
      if (size > 1024) { await reader.cancel(); return reply(413); }
      parts.push(part.value);
    }
    const body = new Uint8Array(size); let offset = 0;
    for (const part of parts) { body.set(part, offset); offset += part.byteLength; }
    try {
      const upstream = await fetchImpl(TARGET, { method: 'POST', redirect: 'manual',
        headers: { 'Content-Type': 'application/json', Origin: request.headers.get('origin'), 'X-OOF-Proxy-Token': env.OOF_ANALYTICS_PROXY_TOKEN }, body });
      return reply([202, 400, 403, 413, 415, 429].includes(upstream.status) ? upstream.status : 503);
    } catch { return reply(503); }
  };
}

export default { fetch: createHandler() };
