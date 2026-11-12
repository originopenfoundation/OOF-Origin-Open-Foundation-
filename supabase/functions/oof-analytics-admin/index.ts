import pg from 'npm:pg@8.23.1';
import { createAdminHandler } from './core.mjs';

const env = (name: string) => Deno.env.get(name) || '';
const projectUrl = env('SUPABASE_URL');
let anonKey = '';
try { anonKey = JSON.parse(env('SUPABASE_PUBLISHABLE_KEYS') || '{}').default || ''; } catch { /* Fail closed. */ }
const permittedUser = env('OOF_ANALYTICS_ADMIN_USER_ID');
let pool: pg.Pool | null = null;
try {
  const url = new URL('postgresql://oof_analytics_writer.zxpufntydcqktylzicky@aws-0-eu-west-2.pooler.supabase.com:6543/postgres');
  const host = url.hostname.toLowerCase();
  const password = env('OOF_ANALYTICS_DATABASE_PASSWORD');
  if (env('OOF_ANALYTICS_ENABLED') === 'true' && password && host === 'aws-0-eu-west-2.pooler.supabase.com') {
    url.password = password;
    pool = new pg.Pool({ connectionString: url.toString(), ssl: { rejectUnauthorized: true }, max: 1,
      connectionTimeoutMillis: 10000, idleTimeoutMillis: 10000 });
  }
} catch { /* Misconfigured storage remains unavailable. */ }

async function authenticate(token: string): Promise<boolean> {
  if (!/^https:\/\/[^/]+\.supabase\.co$/.test(projectUrl) || !anonKey ||
      !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(permittedUser)) return false;
  const response = await fetch(`${projectUrl}/auth/v1/user`, { headers: { apikey: anonKey, Authorization: `Bearer ${token}` },
    signal: AbortSignal.timeout(10000) });
  if (response.status === 401 || response.status === 403) return false;
  if (!response.ok) throw new Error('Auth unavailable');
  const user = await response.json();
  return user.id === permittedUser && !!user.email_confirmed_at && !user.banned_until;
}

async function report(days: number) {
  if (!pool) throw new Error('Storage unavailable');
  const check = await pool.query(`SELECT (current_user='oof_analytics_writer' AND NOT r.rolsuper AND NOT r.rolbypassrls
    AND pg_get_userbyid(c.relowner)<>current_user AND c.relrowsecurity
    AND has_schema_privilege(current_user,n.oid,'USAGE') AND has_table_privilege(current_user,c.oid,'SELECT')
    AND NOT has_schema_privilege('anon',n.oid,'USAGE') AND NOT has_schema_privilege('authenticated',n.oid,'USAGE')) AS safe
    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_roles r ON r.rolname=current_user
    WHERE n.nspname='oof_analytics' AND c.relname='daily_counts'`);
  if (check.rows.length !== 1 || check.rows[0].safe !== true) throw new Error('Unsafe storage');
  const totals = await pool.query(`SELECT event,SUM(count)::int AS count FROM oof_analytics.daily_counts
    WHERE day >= CURRENT_DATE - ($1::int - 1) AND day <= CURRENT_DATE GROUP BY event`, [days]);
  const grouped = await pool.query(`SELECT event,content,content_id AS "contentId",source,language,SUM(count)::int AS count
    FROM oof_analytics.daily_counts WHERE day >= CURRENT_DATE - ($1::int - 1) AND day <= CURRENT_DATE
    GROUP BY event,content,content_id,source,language ORDER BY count DESC LIMIT 10001`, [days]);
  return { status: 'AVAILABLE', rows: grouped.rows.slice(0, 10000), totals: totals.rows,
    rowsTruncated: grouped.rows.length > 10000, visits: null,
    limitation: 'Aggregate events are not verified human visits.' };
}

async function cloudflare(days: number) {
  const account = env('CLOUDFLARE_ACCOUNT_ID'), site = env('CLOUDFLARE_WEB_ANALYTICS_SITE_TAG');
  const token = env('CLOUDFLARE_ANALYTICS_API_TOKEN');
  if (!/^[a-f\d]{32}$/i.test(account) || !/^[a-f\d]{32}$/i.test(site) || !token) return { status: 'NOT_CONFIGURED', rows: null };
  const end = new Date(), start = new Date(end.getTime() - days * 86400000);
  const iso = (date: Date) => date.toISOString().replace(/\.\d{3}Z$/, 'Z');
  const query = `query { viewer { accounts(filter: {accountTag: "${account}"}) {
    rows: rumPageloadEventsAdaptiveGroups(limit: 10000, orderBy: [sum_visits_DESC], filter: {AND: [
      {datetime_geq: "${iso(start)}", datetime_leq: "${iso(end)}"}, {siteTag: "${site}"},
      {requestHost: "originopenfoundation.org"}, {OR: [{bot: 0}, {bot: 1}]}
    ]}) { sum { visits } dimensions { countryName date } } } } }`;
  const response = await fetch('https://api.cloudflare.com/client/v4/graphql', { method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, variables: {} }), signal: AbortSignal.timeout(10000) });
  if (!response.ok) throw new Error('Cloudflare unavailable');
  const result = await response.json(), rows = result?.data?.viewer?.accounts?.[0]?.rows;
  if (result.errors || !Array.isArray(rows) || rows.some((row: any) => !Number.isFinite(row?.sum?.visits) || row.sum.visits < 0)) throw new Error('Cloudflare unavailable');
  return { status: 'AVAILABLE', retrievedAt: end.toISOString(), rowsTruncated: rows.length >= 10000,
    rows: rows.map((row: any) => ({ date: row.dimensions?.date || null, country: row.dimensions?.countryName || 'Unknown', visits: row.sum.visits })),
    requests: null, bandwidth: null, verifiedBots: null, securityEvents: null,
    limitation: 'Cloudflare Web Analytics visits are not HTTP requests or verified humans.' };
}

Deno.serve(createAdminHandler({ authenticate, report, cloudflare }));
