#!/usr/bin/env python3
"""Record hashes for an already validated incident release candidate."""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'data' / 'ai-incidents' / 'public'
OUTPUT = PUBLIC / 'release-manifest.json'


def artifact_hash(path):
    # Git's text checkout may use CRLF locally but LF in the deployed tree.
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def main():
    if '--verify' in sys.argv:
        manifest = json.loads(OUTPUT.read_text(encoding='utf-8'))
        errors = []
        for name, expected in manifest.get('artifactsSha256', {}).items():
            path = (ROOT / name).resolve()
            if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
                errors.append(f'Missing or invalid artifact: {name}')
            elif artifact_hash(path) != expected:
                errors.append(f'Artifact hash mismatch: {name}')
        expected_version = hashlib.sha256(json.dumps(manifest.get('artifactsSha256', {}), sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        if not manifest.get('artifactsSha256') or expected_version != manifest.get('datasetVersion'):
            errors.append('Dataset version does not match artifact inventory')
        if errors:
            raise SystemExit('\n'.join(errors[:50]))
        print(f"Verified {len(manifest['artifactsSha256'])} release artifact hashes")
        return
    summary = json.loads((PUBLIC / 'summary.json').read_text(encoding='utf-8'))
    index = json.loads((PUBLIC / 'incident-index.json').read_text(encoding='utf-8'))
    search = json.loads((PUBLIC / 'incident-search.json').read_text(encoding='utf-8'))
    items = index.get('items', [])
    if len(items) != summary.get('totalIncidents') or len(items) != len(search.get('items', [])):
        raise SystemExit('Incident release candidate counts do not agree')
    paths = sorted(path for path in PUBLIC.rglob('*.json') if path != OUTPUT)
    paths.extend((ROOT / 'ai-incidents').glob('*/index.html'))
    paths.append(ROOT / 'ai-incidents' / 'index.html')
    for item in items:
        path = ROOT / 'ai-incidents' / 'incidents' / item['slug'] / 'index.html'
        if not path.is_file():
            raise SystemExit(f"Missing incident page: {item['id']}")
        paths.append(path)
    paths.extend(ROOT / item for item in ('sitemap.xml', 'search-index.json', 'data/oof-site-knowledge-graph.json',
                                         'assets/js/ai-incidents/app.js', 'assets/js/ai-incidents/repository.js',
                                         'assets/css/oof-ai-incidents.css'))
    artifacts = {path.relative_to(ROOT).as_posix(): artifact_hash(path) for path in sorted(set(paths))}
    version = hashlib.sha256(json.dumps(artifacts, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    payload = {
        'datasetVersion': version,
        'hashAlgorithm': 'SHA-256 over bytes with CRLF normalized to LF',
        'generatedAt': datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        'sourceSnapshot': (summary.get('operationalStatus') or {}).get('latestSourceSnapshot'),
        'incidentCount': len(items),
        'automatedAssessmentCount': summary.get('automatedAnalyses'),
        'validationStatus': 'artifact counts and page presence checked; full workflow validation required',
        'deploymentStatus': 'not established by this manifest',
        'artifactsSha256': artifacts,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f"Recorded {len(artifacts)} artifact hashes for {len(items)} incidents")


if __name__ == '__main__':
    main()
