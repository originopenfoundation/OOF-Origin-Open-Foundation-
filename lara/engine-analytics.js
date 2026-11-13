'use strict';

async function runEngineAnalysis(analysis, env = process.env, transport = fetch) {
  const { GIE_INTERNAL_URL, GIE_SERVICE_TOKEN, GIE_ANALYTICS_TENANT } = env;
  if (!GIE_INTERNAL_URL || !GIE_SERVICE_TOKEN || !GIE_ANALYTICS_TENANT) {
    return { status: 503, body: { error: 'Private analytics service is not configured' } };
  }

  try {
    const url = new URL('/v1/analytics', GIE_INTERNAL_URL);
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) {
      throw new Error('Invalid private service URL');
    }
    const response = await transport(url, {
      method: 'POST',
      headers: { authorization: 'Bearer ' + GIE_SERVICE_TOKEN, 'content-type': 'application/json' },
      body: JSON.stringify({ tenant_id: GIE_ANALYTICS_TENANT, analysis }),
      redirect: 'error',
      signal: AbortSignal.timeout(5000),
    });
    if (response.status === 422) {
      await response.body?.cancel();
      return { status: 422, body: { error: 'Engine rejected the analysis request' } };
    }
    if (!response.ok) {
      await response.body?.cancel();
      throw new Error('Private service refused request');
    }
    const data = await response.json();
    if (data.api_version !== 'v1' || !data.analysis || data.analysis.capability !== analysis.capability) {
      throw new Error('Unexpected engine response');
    }
    return { status: 200, body: data };
  } catch {
    return { status: 502, body: { error: 'Private analytics service is unavailable' } };
  }
}

module.exports = { runEngineAnalysis };
