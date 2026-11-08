"""Read both staged assessment files while retaining legacy compatibility."""
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

ACTIVE_NAME = 'active-intelligence.json'
ARCHIVE_NAME = 'historical-archive.json'


def read_assessments(legacy_path, default=None):
    legacy_path = Path(legacy_path)
    active_path = legacy_path.with_name(ACTIVE_NAME)
    archive_path = legacy_path.with_name(ARCHIVE_NAME)
    active_exists, archive_exists = active_path.exists(), archive_path.exists()
    if active_exists != archive_exists:
        raise ValueError('incomplete incident analysis file pair; refusing to use stale data')
    if not active_exists:
        if not legacy_path.exists():
            return default if default is not None else {'assessments': []}
        return json.loads(legacy_path.read_text(encoding='utf-8'))
    archive_bytes = archive_path.read_bytes()
    active = json.loads(active_path.read_text(encoding='utf-8'))
    expected = active.get('archiveSha256')
    if not expected or hashlib.sha256(archive_bytes).hexdigest() != expected:
        raise ValueError('incident analysis archive hash mismatch; refusing incomplete migration')
    archive = json.loads(archive_bytes)
    return {**active, 'assessments': active.get('assessments', []) + archive.get('assessments', [])}


def write_assessments(legacy_path, payload, warning_mib=None):
    legacy_path = Path(legacy_path)
    warning_mib = int(os.environ.get('OOF_INCIDENT_STORAGE_WARNING_MIB', '80')) if warning_mib is None else warning_mib
    if not 0 < warning_mib < 100:
        raise ValueError('incident storage warning threshold must be between 1 and 99 MiB')
    active_path = legacy_path.with_name(ACTIVE_NAME)
    archive_path = legacy_path.with_name(ARCHIVE_NAME)
    if not active_path.exists() and not archive_path.exists():
        legacy_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        return
    # Validate the current pair before allowing a new one to replace it.
    read_assessments(legacy_path)
    assessments = payload.get('assessments', [])
    latest = {}
    identities = set()
    for item in assessments:
        identity = item['assessmentIdentity']
        if identity in identities:
            raise ValueError('duplicate assessment identity')
        identities.add(identity)
        current = latest.get(item['incidentId'])
        if current is None or item['analysisVersion'] > current['analysisVersion']:
            latest[item['incidentId']] = item
    active_ids = {item['assessmentIdentity'] for item in latest.values()}
    historical = [item for item in assessments if item['assessmentIdentity'] not in active_ids]
    archive = {'schemaVersion': payload.get('schemaVersion'), 'assessments': historical}
    archive_bytes = (json.dumps(archive, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')
    active = {key: value for key, value in payload.items() if key not in ('assessments', 'archiveSha256')}
    active['archiveSha256'] = hashlib.sha256(archive_bytes).hexdigest()
    active['assessments'] = [item for item in assessments if item['assessmentIdentity'] in active_ids]
    active_bytes = (json.dumps(active, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')
    if max(len(active_bytes), len(archive_bytes)) >= warning_mib * 1024 * 1024:
        raise ValueError('incident analysis file reaches size warning threshold; no data written')
    # Git publishes both tracked files together; local failures restore the old pair.
    with tempfile.TemporaryDirectory(prefix='incident-pair-', dir=legacy_path.parent) as temp:
        temp = Path(temp)
        old_active, old_archive = temp / 'active.old', temp / 'archive.old'
        new_active, new_archive = temp / 'active.new', temp / 'archive.new'
        shutil.copy2(active_path, old_active)
        shutil.copy2(archive_path, old_archive)
        new_active.write_bytes(active_bytes)
        new_archive.write_bytes(archive_bytes)
        try:
            os.replace(new_archive, archive_path)
            os.replace(new_active, active_path)
            read_assessments(legacy_path)
        except Exception:
            shutil.copy2(old_archive, archive_path)
            shutil.copy2(old_active, active_path)
            raise
