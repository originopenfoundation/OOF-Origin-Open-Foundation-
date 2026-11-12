const ORIGINS = new Set(['https://originopenfoundation.org', 'https://www.originopenfoundation.org']);

export function createAdminHandler({ authenticate, report, cloudflare }) {
  return async request => {
    const origin = request.headers.get('origin');
    const cors = ORIGINS.has(origin) ? { 'Access-Control-Allow-Origin': origin, Vary: 'Origin' } : {};
    const headers = { ...cors, 'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' };
    const reply = (status, value) => new Response(JSON.stringify(value), { status, headers });
    if (origin && !ORIGINS.has(origin)) return reply(403, { error: 'Forbidden' });
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: { ...cors,
      'Access-Control-Allow-Methods': 'GET, OPTIONS', 'Access-Control-Allow-Headers': 'Authorization, apikey', 'Access-Control-Max-Age': '600' } });
    if (request.method !== 'GET') return reply(405, { error: 'Method not allowed' });
    const authorization = request.headers.get('authorization') || '';
    if (!/^Bearer [A-Za-z0-9._-]+$/.test(authorization)) return reply(401, { error: 'Unauthorized' });
    try { if (!await authenticate(authorization.slice(7))) return reply(401, { error: 'Unauthorized' }); }
    catch { return reply(503, { error: 'Authentication unavailable' }); }
    const query = new URL(request.url).searchParams;
    if ([...query.keys()].some(key => key !== 'days') || query.getAll('days').length > 1) return reply(400, { error: 'Invalid request' });
    const days = Number(query.get('days') || '30');
    if (![7, 30, 90].includes(days)) return reply(400, { error: 'Invalid date range' });
    const [independent, cloudflareData] = await Promise.all([
      report(days).catch(() => ({ status: 'UNAVAILABLE', rows: null })),
      cloudflare(days).catch(() => ({ status: 'UNAVAILABLE', rows: null })),
    ]);
    return reply(200, { independent, cloudflare: cloudflareData });
  };
}
