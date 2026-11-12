const EVENTS = new Set(['page_view', 'architecture_opened', 'standard_viewed', 'module_viewed',
  'document_downloaded', 'search_results', 'search_no_results', 'search_result_selected',
  'lara_opened', 'product_opened', 'contact_selected']);
const CONTENT = new Set(['home', 'architecture', 'standard', 'module', 'methodology', 'document', 'product', 'search', 'lara', 'other']);
const SOURCES = new Set(['google', 'bing', 'x', 'chatgpt', 'other_ai', 'other_website', 'direct_or_unknown', 'internal']);
const LANGUAGES = new Set(['en', 'de', 'fr', 'es', 'pt', 'hi', 'ja', 'zh', 'ko', 'ru', 'it', 'ar', 'other']);
const FIELDS = new Set(['event', 'content', 'source', 'language', 'contentId']);
const ALLOWED_ORIGINS = new Set(['https://originopenfoundation.org', 'https://www.originopenfoundation.org']);

function validEvent(value, catalog) {
  if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).some(k => !FIELDS.has(k))) return false;
  if (!EVENTS.has(value.event) || !CONTENT.has(value.content) || !SOURCES.has(value.source) || !LANGUAGES.has(value.language)) return false;
  return value.contentId === undefined || (typeof value.contentId === 'string' && catalog.get(value.contentId) === value.content);
}

async function boundedBody(request) {
  if (!request.body || Number(request.headers.get('content-length') || 0) > 1024) throw new Error('Invalid body');
  const reader = request.body.getReader();
  const decoder = new TextDecoder('utf-8', { fatal: true });
  let size = 0, text = '';
  for (;;) {
    const part = await reader.read();
    if (part.done) break;
    size += part.value.byteLength;
    if (size > 1024) { await reader.cancel(); throw new Error('Invalid body'); }
    text += decoder.decode(part.value, { stream: true });
  }
  text += decoder.decode();
  return JSON.parse(text);
}

export function createCollector({ storage, catalog, authorize, originRequired = true }) {
  return async request => {
    const origin = request.headers.get('origin');
    const cors = ALLOWED_ORIGINS.has(origin) ? { 'Access-Control-Allow-Origin': origin, Vary: 'Origin' } : {};
    const reply = (status, body = '') => new Response(body, { status, headers: { ...cors, 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' } });
    if ((originRequired && !ALLOWED_ORIGINS.has(origin)) || (origin && !ALLOWED_ORIGINS.has(origin))) return reply(403);
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: { ...cors, 'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Max-Age': '600' } });
    if (request.method !== 'POST') return reply(405);
    if (authorize && !await authorize(request)) return reply(403);
    if (!/^application\/json(?:\s*;|$)/i.test(request.headers.get('content-type') || '')) return reply(415);
    let value;
    try { value = await boundedBody(request); } catch { return reply(400); }
    let allowed = new Map();
    try { allowed = await catalog(); } catch { /* Identity events fail closed. */ }
    if (!validEvent(value, allowed)) return reply(400);
    try { await storage.record(value); return reply(202); } catch { return reply(503); }
  };
}

export { validEvent };
