"""Bounded AVID reference discovery; records are never published as incidents."""
import json
import re
from datetime import datetime, timezone
from urllib.request import Request, urlopen

API = 'https://api.github.com/repos/avidml/avid-db'
RAW = 'https://raw.githubusercontent.com/avidml/avid-db'
PATH = re.compile(r'^reports/\d{4}/AVID-\d{4}-R\d+\.json$')
SHA = re.compile(r'^[0-9a-f]{40}$')


def request_json(url):
    request = Request(url, headers={'User-Agent': 'OOF-Incident-Sync/1.0', 'Accept': 'application/vnd.github+json'})
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def discover(fetch=request_json, limit=5):
    commits = fetch(f'{API}/commits?path=reports&per_page={max(1, min(limit, 10))}')
    if not isinstance(commits, list):
        raise ValueError('AVID commit response is not a list')
    references = []
    seen = set()
    for commit in commits:
        sha = str(commit.get('sha') or '')
        if not SHA.fullmatch(sha):
            raise ValueError('AVID returned an invalid commit identifier')
        detail = fetch(f'{API}/commits/{sha}')
        for item in detail.get('files', []):
            path = item.get('filename', '')
            if item.get('status') == 'removed' or not PATH.fullmatch(path) or path in seen:
                continue
            seen.add(path)
            report = fetch(f'{RAW}/{sha}/{path}')
            identifier = (report.get('metadata') or {}).get('report_id')
            if identifier != path.rsplit('/', 1)[-1][:-5]:
                raise ValueError('AVID report identifier does not match its path')
            problem = report.get('problemtype') or {}
            references.append({'sourceId': identifier, 'type': problem.get('type') or 'Unknown',
                               'reportedDate': report.get('reported_date'),
                               'url': f'https://github.com/avidml/avid-db/blob/{sha}/{path}',
                               'disposition': 'INTERNAL_REFERENCE',
                               'independentCorroboration': False})
    return {'attemptedAt': datetime.now(timezone.utc).isoformat(), 'recordsRetrieved': len(references),
            'latestCommit': commits[0].get('sha') if commits else None, 'references': references,
            'limitation': 'Bounded recent repository commits only; records are not established incidents or independent corroboration.'}
