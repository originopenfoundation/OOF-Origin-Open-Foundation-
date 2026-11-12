const TARGET = 'https://zxpufntydcqktylzicky.supabase.co/functions/v1/oof-analytics';
const ORIGINS = new Set(['https://originopenfoundation.org', 'https://www.originopenfoundation.org']);

export function createHandler(fetchImpl = fetch) {
  return async (request, env) => {
    const url = new URL(request.url);
    const reply = status => new Response(null, { status, headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' } });
    if (!ORIGINS.has(url.origin) || url.pathname !== '/_oof/analytics/event' || url.search || url.hash) return reply(404);
    if (request.method !== 'POST') return reply(405);
    if (!ORIGINS.has(request.headers.get('origin'))) return reply(403);
    if (!/^application\/json(?:\s*;|$)/i.test(request.headers.get('content-type') || '')) return reply(415);
    if (typeof env.OOF_ANALYTICS_PROXY_TOKEN !== 'string' || env.OOF_ANALYTICS_PROXY_TOKEN.length < 43) return reply(503);
    if (!request.body || Number(request.headers.get('content-length') || 0) > 1024) return reply(413);
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
      const upstream = await fetchImpl(TARGET, { method: 'POST', redirect: 'error',
        headers: { 'Content-Type': 'application/json', Origin: request.headers.get('origin'), 'X-OOF-Proxy-Token': env.OOF_ANALYTICS_PROXY_TOKEN }, body });
      return reply([202, 400, 403, 413, 415, 429].includes(upstream.status) ? upstream.status : 503);
    } catch { return reply(503); }
  };
}

export default { fetch: createHandler() };
