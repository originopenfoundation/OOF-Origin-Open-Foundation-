(() => {
  'use strict';
  const api = 'https://zxpufntydcqktylzicky.supabase.co';
  // Supabase identifies this as a publishable key; it grants no administrative authority.
  const publicKey = 'sb_publishable_hqt09k0Mf8soMOc2OX3OGA_jvVuPnpb';
  const $ = selector => document.querySelector(selector);
  const status = $('#status'), login = $('#login'), setup = $('#setup'), dashboard = $('#dashboard');
  const fragments = new URLSearchParams(location.hash.slice(1));
  let invitation = fragments.get('type') === 'invite' ? fragments.get('access_token') : null;
  let session = null, current = null;
  if (location.hash) history.replaceState(null, '', location.pathname + location.search);
  if (invitation) { login.hidden = true; setup.hidden = false; }
  const headers = { apikey: publicKey, 'Content-Type': 'application/json' };
  const request = (url, options) => fetch(url, { ...options, cache: 'no-store', credentials: 'omit', referrerPolicy: 'no-referrer' });
  setup.addEventListener('submit', async event => {
    event.preventDefault();
    const input = $('#new-password');
    try {
      const response = await request(api + '/auth/v1/user', { method: 'PUT', headers: { ...headers, Authorization: 'Bearer ' + invitation }, body: JSON.stringify({ password: input.value }) });
      if (!response.ok) throw new Error('The invitation is invalid or expired.');
      invitation = null; input.value = ''; setup.hidden = true; login.hidden = false;
      status.textContent = 'Password set. Sign in to continue.';
    } catch (error) { status.textContent = error.message; }
  });
  login.addEventListener('submit', async event => {
    event.preventDefault();
    const password = $('#password');
    try {
      const response = await request(api + '/auth/v1/token?grant_type=password', { method: 'POST', headers,
        body: JSON.stringify({ email: $('#email').value, password: password.value }) });
      password.value = '';
      if (!response.ok) throw new Error('Sign in failed. Check your credentials.');
      const result = await response.json();
      if (!result.access_token) throw new Error('Sign in is unavailable.');
      session = result.access_token; login.hidden = true; dashboard.hidden = false; await refresh();
    } catch (error) { password.value = ''; status.textContent = error.message; }
  });
  function row(source, metric, value) {
    const tr = document.createElement('tr');
    for (const text of [source, metric, value]) { const td = document.createElement('td'); td.textContent = String(text); tr.append(td); }
    $('#rows').append(tr);
  }
  async function refresh() {
    if (!session) return;
    status.textContent = 'Loading...';
    try {
      const response = await request(api + '/functions/v1/oof-analytics-admin?days=' + encodeURIComponent($('#range').value),
        { headers: { apikey: publicKey, Authorization: 'Bearer ' + session } });
      if (!response.ok) throw new Error('Analytics unavailable or access denied.');
      current = await response.json(); $('#rows').replaceChildren(); $('#breakdown').replaceChildren();
      const cf = current.cloudflare, first = current.independent;
      row('Cloudflare Web Analytics', 'Visits', cf.rows ? (cf.rowsTruncated ? 'At least ' : '') + cf.rows.reduce((sum, item) => sum + item.visits, 0) : 'Unavailable');
      row('Cloudflare', 'Requests / bandwidth / verified bots', 'Unavailable');
      row('Independent analytics', 'Page views', first.totals ? first.totals.filter(item => item.event === 'page_view').reduce((sum, item) => sum + item.count, 0) : 'Unavailable');
      row('Independent analytics', 'Observed events', first.totals ? first.totals.filter(item => item.event !== 'page_view').reduce((sum, item) => sum + item.count, 0) : 'Unavailable');
      row('Independent analytics', 'Estimated visitors', 'Unavailable');
      const countries = new Map(), sources = new Map(), content = new Map();
      for (const item of cf.rows || []) countries.set(item.country, (countries.get(item.country) || 0) + item.visits);
      for (const item of first.rows || []) if (item.event === 'page_view') {
        sources.set(item.source, (sources.get(item.source) || 0) + item.count);
        const key = item.contentId || item.content; content.set(key, (content.get(key) || 0) + item.count);
      }
      for (const [label, values] of [['Cloudflare country', countries], ['Independent source', sources], ['Independent content', content]]) {
        for (const [name, count] of [...values].sort((a, b) => b[1] - a[1]).slice(0, 10)) row(label, name, count);
      }
      const totals = first.totals || [];
      if (totals.length) {
        const h = document.createElement('h2'); h.textContent = 'Observed events'; $('#breakdown').append(h);
        const max = Math.max(...totals.map(item => item.count), 1);
        for (const item of totals) { const p = document.createElement('p'), bar = document.createElement('progress');
          p.textContent = item.event + ': ' + item.count + ' '; bar.max = max; bar.value = item.count; bar.setAttribute('aria-label', item.event); p.append(bar); $('#breakdown').append(p); }
      }
      status.textContent = `Cloudflare: ${cf.status} | Independent: ${first.status}${first.rowsTruncated ? ' | Breakdowns truncated' : ''}`;
      $('#export').disabled = false;
    } catch (error) { current = null; $('#export').disabled = true; status.textContent = error.message; }
  }
  $('#refresh').addEventListener('click', refresh);
  $('#logout').addEventListener('click', async () => {
    const token = session;
    session = null; current = null; dashboard.hidden = true; login.hidden = false;
    $('#rows').replaceChildren(); $('#breakdown').replaceChildren(); $('#export').disabled = true;
    try {
      const response = await request(api + '/auth/v1/logout', { method: 'POST', headers: { apikey: publicKey, Authorization: 'Bearer ' + token } });
      status.textContent = response.ok ? 'Signed out.' : 'Signed out locally; server session could not be revoked.';
    } catch { status.textContent = 'Signed out locally; server session could not be revoked.'; }
  });
  $('#export').addEventListener('click', () => {
    if (!current) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(current, null, 2)], { type: 'application/json' }));
    const link = document.createElement('a'); link.href = url; link.download = 'oof-analytics-aggregates.json'; link.click(); URL.revokeObjectURL(url);
  });
})();
