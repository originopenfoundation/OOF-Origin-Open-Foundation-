#!/usr/bin/env python3
"""Run checks without writing generated audit reports into the repository."""

import sys
import tempfile
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {'discovery', 'incident'}:
        raise SystemExit('Expected discovery or incident')
    mode = sys.argv[1]
    with tempfile.TemporaryDirectory(prefix='oof-ci-audits-') as directory:
        root = Path(directory)
        if mode == 'discovery':
            import audit_discovery_infrastructure as audit
            audit.REPORT_PATH = root / 'discovery.json'
            sys.argv = [sys.argv[0], '--strict']
            return audit.main()
        import audit_ai_incident_methodology as methodology
        import audit_ai_incident_v341 as independent
        methodology.JSON_REPORT = root / 'methodology.json'
        methodology.MARKDOWN_REPORT = root / 'methodology.md'
        methodology.STAGE_A_JSON_REPORT = root / 'stage-a.json'
        methodology.STAGE_A_REPORT = root / 'stage-a.md'
        independent.REPORT = root / 'independent.json'
        independent.MARKDOWN = root / 'independent.md'
        result = methodology.main()
        independent.run()
        return result


if __name__ == '__main__':
    raise SystemExit(main())
