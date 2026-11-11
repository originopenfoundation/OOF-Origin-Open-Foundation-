"""Read both staged assessment files while retaining legacy compatibility."""
import hashlib
import json
import os
import shutil
from pathlib import Path

ACTIVE_NAME = 'active-intelligence.json'
ARCHIVE_NAME = 'historical-archive.json'
RECOVERY_NAME = '.incident-analysis-recovery'


def _valid_pair(active_path, archive_path):
    try:
        active = json.loads(active_path.read_text(encoding='utf-8'))
        data = archive_path.read_bytes()
        json.loads(data)
        return bool(active.get('archiveSha256')) and hashlib.sha256(data).hexdigest() == active['archiveSha256']
    except (OSError, ValueError, TypeError):
        return False


def recover_interrupted_write(legacy_path):
    legacy_path = Path(legacy_path)
    recovery = legacy_path.parent / RECOVERY_NAME
    if not recovery.exists():
        return False
    old_active, old_archive = recovery / 'active.old', recovery / 'archive.old'
    active, archive = legacy_path.with_name(ACTIVE_NAME), legacy_path.with_name(ARCHIVE_NAME)
    backup_valid = _valid_pair(old_active, old_archive)
    current_valid = _valid_pair(active, archive)
    if not backup_valid and not current_valid:
        raise ValueError('invalid incident recovery backup; manual review required')
    restored = not current_valid
    if restored:
        shutil.copy2(old_archive, archive)
        shutil.copy2(old_active, active)
        if not _valid_pair(active, archive):
            raise ValueError('incident storage recovery failed')
    for name in ('active.old', 'archive.old', 'active.new', 'archive.new'):
        path = recovery / name
        if path.exists():
            path.unlink()
    recovery.rmdir()
    return restored


def read_assessments(legacy_path, default=None):
    legacy_path = Path(legacy_path)
    if (legacy_path.parent / RECOVERY_NAME).exists():
        raise ValueError('incident storage transaction requires recovery before reading')
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
    return {**active, 'relevanceHistory': archive.get('relevanceHistory', []),
            'assessments': active.get('assessments', []) + archive.get('assessments', [])}


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
    recover_interrupted_write(legacy_path)
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
    relevance = payload.get('relevanceByIncident') or {}
    active_ids = {
        item['assessmentIdentity'] for incident_id, item in latest.items()
        if relevance.get(incident_id, {}).get('status') not in ('INACTIVE', 'EXCLUDED')
    }
    historical = [item for item in assessments if item['assessmentIdentity'] not in active_ids]
    archive = {'schemaVersion': payload.get('schemaVersion'), 'assessments': historical,
               'relevanceHistory': payload.get('relevanceHistory', [])}
    archive_bytes = (json.dumps(archive, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')
    active = {key: value for key, value in payload.items() if key not in ('assessments', 'archiveSha256', 'relevanceHistory')}
    active['archiveSha256'] = hashlib.sha256(archive_bytes).hexdigest()
    active['assessments'] = [item for item in assessments if item['assessmentIdentity'] in active_ids]
    active_bytes = (json.dumps(active, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')
    if max(len(active_bytes), len(archive_bytes)) >= warning_mib * 1024 * 1024:
        raise ValueError('incident analysis file reaches size warning threshold; no data written')
    recovery = legacy_path.parent / RECOVERY_NAME
    recovery.mkdir()
    old_active, old_archive = recovery / 'active.old', recovery / 'archive.old'
    new_active, new_archive = recovery / 'active.new', recovery / 'archive.new'
    try:
        shutil.copy2(active_path, old_active)
        shutil.copy2(archive_path, old_archive)
        new_active.write_bytes(active_bytes)
        new_archive.write_bytes(archive_bytes)
        if not _valid_pair(old_active, old_archive) or not _valid_pair(new_active, new_archive):
            raise ValueError('incident storage transaction validation failed')
        os.replace(new_archive, archive_path)
        os.replace(new_active, active_path)
        recover_interrupted_write(legacy_path)
    except Exception:
        if _valid_pair(old_active, old_archive):
            recover_interrupted_write(legacy_path)
        raise
