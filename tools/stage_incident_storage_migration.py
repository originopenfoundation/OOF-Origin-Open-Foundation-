#!/usr/bin/env python3
"""Stage and reconcile a two-file incident analysis migration without publishing it."""
import argparse
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

try:
    from tools.audit_incident_storage_capacity import STORE, INCIDENTS, inventory
    from tools.incident_relevance import classify_relevance
except ModuleNotFoundError:
    from audit_incident_storage_capacity import STORE, INCIDENTS, inventory
    from incident_relevance import classify_relevance


def digest(item):
    return hashlib.sha256(json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def stage(destination, store_path=STORE, incidents_path=INCIDENTS, warning_mib=80):
    destination = Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('staging directory must be empty; existing evidence will not be overwritten')
    report = inventory(store_path, incidents_path, warning_mib)
    for key in ('duplicateAssessmentIds', 'duplicateIncidentVersions', 'unknownIncidentIds', 'missingSupersedes'):
        if report[key]:
            raise ValueError(f'migration blocked: {key}: {report[key][:5]}')
    if max(report['estimatedActiveBytes'], report['estimatedArchiveBytes']) >= warning_mib * 1024 * 1024:
        raise ValueError('migration blocked: estimated file size reaches warning threshold')
    destination.mkdir(parents=True, exist_ok=True)
    backup = destination / 'analysis-store.backup.json'
    shutil.copy2(store_path, backup)
    if hashlib.sha256(backup.read_bytes()).hexdigest() != report['sourceSha256']:
        raise ValueError('backup hash mismatch')
    original = json.loads(backup.read_text(encoding='utf-8'))
    items = original['assessments']
    latest = {}
    for item in items:
        previous = latest.get(item['incidentId'])
        if previous is None or item['analysisVersion'] > previous['analysisVersion']:
            latest[item['incidentId']] = item
    active_ids = {item['assessmentIdentity'] for item in latest.values()}
    metadata = {key: value for key, value in original.items() if key != 'assessments'}
    records = json.loads(incidents_path.read_text(encoding='utf-8'))['incidents']
    relevance = {record['id']: classify_relevance(record) for record in records}
    active = {**metadata, 'relevanceByIncident': relevance,
              'assessments': [item for item in items if item['assessmentIdentity'] in active_ids]}
    archive = {'schemaVersion': original.get('schemaVersion'), 'assessments': [item for item in items if item['assessmentIdentity'] not in active_ids]}
    paths = [destination / 'active-intelligence.json', destination / 'historical-archive.json']
    paths[1].write_text(json.dumps(archive, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8', newline='\n')
    active['archiveSha256'] = hashlib.sha256(paths[1].read_bytes()).hexdigest()
    paths[0].write_text(json.dumps(active, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8', newline='\n')
    restored = []
    for path in paths:
        if path.stat().st_size >= warning_mib * 1024 * 1024:
            raise ValueError(f'staged file reaches warning threshold: {path.name}')
        restored.extend(json.loads(path.read_text(encoding='utf-8'))['assessments'])
    if Counter(map(digest, items)) != Counter(map(digest, restored)):
        raise ValueError('staged records do not match original content')
    return {**report, 'status': 'STAGED_NOT_PUBLISHED', 'actualActiveBytes': paths[0].stat().st_size,
            'actualArchiveBytes': paths[1].stat().st_size, 'verifiedAssessmentCount': len(restored),
            'relevanceCounts': dict(Counter(item['status'] for item in relevance.values())),
            'backup': str(backup), 'readerAndPublicationAcceptance': 'NOT_VERIFIED'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--warning-mib', type=int, default=80)
    args = parser.parse_args()
    if not 0 < args.warning_mib < 100:
        parser.error('--warning-mib must be between 1 and 99')
    print(json.dumps(stage(args.destination, warning_mib=args.warning_mib), ensure_ascii=False, indent=2))
