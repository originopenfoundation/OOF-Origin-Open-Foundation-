(() => {
  'use strict';
  const configUrl = '/assets/data/oof-analytics-config.json';
  const language = (document.documentElement.lang || 'en').toLowerCase().split('-')[0];
  const languages = new Set(['en','de','fr','es','pt','hi','ja','zh','ko','ru','it','ar']);
  const page = location.pathname.toLowerCase();
  let content = page.includes('architecture') ? 'architecture' : page.includes('module') ? 'module' :
    page.includes('standard') ? 'standard' : page.includes('methodolog') ? 'methodology' :
    page.startsWith('/products') ? 'product' : page === '/' || page === '/index.html' ? 'home' : 'other';
  function source() {
    try {
      if (!document.referrer) return 'direct_or_unknown';
      const host = new URL(document.referrer).hostname.toLowerCase();
      if (host === location.hostname) return 'internal';
      if (['google.com','www.google.com','www.google.sk','www.google.de','www.google.fr','www.google.es',
        'www.google.co.uk','www.google.co.jp','www.google.com.br','www.google.co.in'].includes(host)) return 'google';
      if (host === 'bing.com' || host.endsWith('.bing.com')) return 'bing';
      if (['x.com','www.x.com','twitter.com','t.co'].includes(host)) return 'x';
      if (['chatgpt.com','chat.openai.com'].includes(host)) return 'chatgpt';
      if (['claude.ai','perplexity.ai','www.perplexity.ai'].includes(host)) return 'other_ai';
      return 'other_website';
    } catch { return 'direct_or_unknown'; }
  }
  const sourceCategory = source();
  fetch(configUrl, { credentials: 'omit', referrerPolicy: 'no-referrer', cache: 'no-cache' }).then(response => response.ok ? response.json() : null).then(async config => {
    if (!config || config.enabled !== true || navigator.doNotTrack === '1' || navigator.globalPrivacyControl === true) return;
    const endpoint = new URL(config.endpoint, location.origin);
    if (endpoint.origin !== location.origin || endpoint.pathname !== '/_oof/analytics/event' || endpoint.search || endpoint.hash) return;
    let identity = null;
    try {
      const response = await fetch('/assets/data/oof-analytics-catalog.json', { credentials: 'omit', referrerPolicy: 'no-referrer' });
      const catalog = response.ok ? await response.json() : {};
      const item = catalog[location.pathname];
      if (item && typeof item.id === 'string' && ['architecture', 'standard', 'module'].includes(item.content)) {
        identity = item.id;
        content = item.content;
      }
    } catch { /* General categories remain available when the catalog is unavailable. */ }
    function send(event, section = content) {
      const body = JSON.stringify({ event, content: section, source: sourceCategory, language: languages.has(language) ? language : 'other',
        ...(identity && section === content ? { contentId: identity } : {}) });
      fetch(endpoint.href, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body,
        credentials: 'omit', referrerPolicy: 'no-referrer', keepalive: true }).catch(() => {});
    }
    send('page_view');
    if (content === 'architecture') send('architecture_opened');
    if (content === 'standard') send('standard_viewed');
    if (content === 'module') send('module_viewed');
    if (content === 'product') send('product_opened');
    document.addEventListener('oof:search-results', event => send(event.detail?.hasResults ? 'search_results' : 'search_no_results', 'search'));
    document.addEventListener('click', event => {
      const target = event.target instanceof Element ? event.target : null;
      if (!target) return;
      if (target.closest('.site-search-result')) send('search_result_selected', 'search');
      else if (target.closest('.lara-launch')) send('lara_opened', 'lara');
      else if (target.closest('a[href^="mailto:"]')) send('contact_selected');
      else if (target.closest('a[href$=".pdf"],a[download]')) send('document_downloaded', 'document');
    });
  }).catch(() => {});
})();
