#!/usr/bin/env python3
"""Read-only migration inventory for the incident assessment store."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / 'data' / 'ai-incidents' / 'analysis-store.json'
INCIDENTS = ROOT / 'data' / 'ai-incidents' / 'incident-store.json'


def compact_size(value):
    return len(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')) + 1


def inventory(store_path=STORE, incidents_path=INCIDENTS, warning_mib=80):
    raw = store_path.read_bytes()
    store = json.loads(raw)
    incidents = json.loads(incidents_path.read_text(encoding='utf-8'))['incidents']
    assessments = store['assessments']
    incident_ids = {item['id'] for item in incidents}
    identities = Counter(item['assessmentIdentity'] for item in assessments)
    versions = Counter((item['incidentId'], item['analysisVersion']) for item in assessments)
    latest = {}
    for item in assessments:
        previous = latest.get(item['incidentId'])
        if previous is None or item['analysisVersion'] > previous['analysisVersion']:
            latest[item['incidentId']] = item
    active_ids = {id(item) for item in latest.values()}
    active = [item for item in assessments if id(item) in active_ids]
    archive = [item for item in assessments if id(item) not in active_ids]
    metadata = {key: value for key, value in store.items() if key != 'assessments'}
    active_size = compact_size({**metadata, 'assessments': active})
    archive_size = compact_size({'schemaVersion': store.get('schemaVersion'), 'assessments': archive})
    warning_bytes = warning_mib * 1024 * 1024
    return {
        'sourceSha256': hashlib.sha256(raw).hexdigest(), 'sourceBytes': len(raw),
        'incidentCount': len(incidents), 'assessmentCount': len(assessments),
        'activeAssessmentCount': len(active), 'historicalAssessmentCount': len(archive),
        'estimatedActiveBytes': active_size, 'estimatedArchiveBytes': archive_size,
        'warningThresholdBytes': warning_bytes,
        'archiveHeadroomToWarningBytes': max(0, warning_bytes - archive_size),
        'duplicateAssessmentIds': [key for key, count in identities.items() if count > 1],
        'duplicateIncidentVersions': [list(key) for key, count in versions.items() if count > 1],
        'unknownIncidentIds': sorted({item['incidentId'] for item in assessments} - incident_ids),
        'missingSupersedes': sorted({item['supersedes'] for item in assessments if item.get('supersedes') and item['supersedes'] not in identities}),
        'status': 'INVENTORY_ONLY_NOT_MIGRATED',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--warning-mib', type=int, default=80)
    args = parser.parse_args()
    if not 0 < args.warning_mib < 100:
        parser.error('--warning-mib must be between 1 and 99')
    print(json.dumps(inventory(warning_mib=args.warning_mib), ensure_ascii=False, indent=2))
