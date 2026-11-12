import pg from 'npm:pg@8.23.1';
import { createCollector } from './core.mjs';

// This collector remains unavailable until the operator explicitly enables it.
const enabled = Deno.env.get('OOF_ANALYTICS_ENABLED') === 'true';
const connection = 'postgresql://oof_analytics_writer.zxpufntydcqktylzicky@aws-0-eu-west-2.pooler.supabase.com:6543/postgres';
const password = Deno.env.get('OOF_ANALYTICS_DATABASE_PASSWORD') || '';
let pool: pg.Pool | null = null;
try {
  const url = new URL(connection);
  const host = url.hostname.toLowerCase();
  if (enabled && password && host === 'aws-0-eu-west-2.pooler.supabase.com') {
    url.password = password;
    pool = new pg.Pool({ connectionString: url.toString(), ssl: { rejectUnauthorized: true },
      max: 1, connectionTimeoutMillis: 10000, idleTimeoutMillis: 10000 });
  }
} catch { /* Misconfiguration is reported as unavailable. */ }

let permitted: Promise<boolean> | null = null;
async function verifyPermissions(): Promise<boolean> {
  if (!pool) return false;
  if (!permitted) permitted = pool.query(`SELECT
    (current_user='oof_analytics_writer' AND NOT r.rolsuper AND NOT r.rolbypassrls
     AND pg_get_userbyid(c.relowner)<>current_user AND c.relrowsecurity
     AND has_schema_privilege(current_user,n.oid,'USAGE')
     AND has_table_privilege(current_user,c.oid,'SELECT')
     AND has_table_privilege(current_user,c.oid,'INSERT')
     AND has_table_privilege(current_user,c.oid,'UPDATE')
     AND has_table_privilege(current_user,c.oid,'DELETE')
     AND NOT has_schema_privilege('anon',n.oid,'USAGE')
     AND NOT has_schema_privilege('authenticated',n.oid,'USAGE')) AS safe
    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    JOIN pg_roles r ON r.rolname=current_user
    WHERE n.nspname='oof_analytics' AND c.relname='daily_counts'`)
    .then((result: { rows: { safe: boolean }[] }) => result.rows.length === 1 && result.rows[0].safe === true)
    .catch(() => false);
  const result = await permitted;
  if (!result) permitted = null;
  return result === true;
}

let cachedCatalog: { expires: number; values: Map<string, string> } | null = null;
async function catalog(): Promise<Map<string, string>> {
  if (cachedCatalog && cachedCatalog.expires > Date.now()) return cachedCatalog.values;
  const response = await fetch('https://originopenfoundation.org/assets/data/oof-analytics-catalog.json', {
    signal: AbortSignal.timeout(5000), redirect: 'error',
  });
  if (!response.ok) throw new Error('Catalog unavailable');
  const entries = await response.json();
  const values = new Map<string, string>();
  for (const item of Object.values(entries) as { id?: string; content?: string }[]) {
    if (item?.id && item.content) values.set(item.id, item.content);
  }
  cachedCatalog = { expires: Date.now() + 300000, values };
  return values;
}

const storage = {
  async record(event: { event: string; content: string; contentId?: string; source: string; language: string }) {
    if (!pool || !(await verifyPermissions())) throw new Error('Storage unavailable');
    await pool.query(`INSERT INTO oof_analytics.daily_counts(day,event,content,content_id,source,language,count)
      VALUES(CURRENT_DATE,$1,$2,$3,$4,$5,1)
      ON CONFLICT(day,event,content,content_id,source,language)
      DO UPDATE SET count=oof_analytics.daily_counts.count+1`,
    [event.event, event.content, event.contentId || '', event.source, event.language]);
  },
};

async function authorize(request: Request): Promise<boolean> {
  const expected = Deno.env.get('OOF_ANALYTICS_PROXY_TOKEN') || '';
  const supplied = request.headers.get('x-oof-proxy-token') || '';
  if (expected.length < 43 || supplied.length !== expected.length) return false;
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(expected), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const [left, right] = await Promise.all([expected, supplied].map(value => crypto.subtle.sign('HMAC', key, new TextEncoder().encode(value))));
  const a = new Uint8Array(left), b = new Uint8Array(right);
  let mismatch = 0;
  for (let i = 0; i < a.length; i++) mismatch |= a[i] ^ b[i];
  return mismatch === 0;
}

Deno.serve(createCollector({ storage, catalog, authorize }));
