'use strict';
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const objects = JSON.parse(fs.readFileSync(path.join(root, 'data/knowledge/objects-core.json'), 'utf8')).objects;
const types = { Architecture: 'architecture', ParentStandard: 'standard', CoreModule: 'module' };
const paths = new Map();
for (const item of objects) {
  if (item.visibility !== 'public' || item.authorityState !== 'CANONICAL_AUTHORITATIVE' || !types[item.artifactType]) continue;
  try {
    const url = new URL(item.canonicalUrl);
    if (url.origin !== 'https://originopenfoundation.org' || url.search || url.hash) continue;
    const entry = { id: item.id, content: types[item.artifactType] };
    if (paths.has(url.pathname)) paths.set(url.pathname, null);
    else paths.set(url.pathname, entry);
  } catch { /* An invalid or ambiguous canonical URL is not tracked. */ }
}
const result = Object.fromEntries([...paths].filter(([, value]) => value).sort(([a], [b]) => a.localeCompare(b)));
fs.writeFileSync(path.join(root, 'assets/data/oof-analytics-catalog.json'), JSON.stringify(result) + '\n');
console.log(`Prepared ${Object.keys(result).length} unambiguous public canonical references.`);
