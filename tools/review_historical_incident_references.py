#!/usr/bin/env python3
"""Record archival citation integrity without granting historical authority."""
import hashlib
from pathlib import Path
import incident_intelligence_v2 as engine


def main():
    reviews = []
    errors = engine.validate(historical_reviews=reviews)
    report = {
        'schemaVersion': '1.0',
        'policy': 'Superseded citations may be retained only with matching identity, ownership, URL, name, source digest and recorded build identity.',
        'rootCause': 'Current canonical eligibility was applied to superseded source snapshots as if retention reasserted their authority.',
        'authorityReestablished': False,
        'automaticApproval': False,
        'sourceHistoryModified': False,
        'analysisStoreSha256': hashlib.sha256(engine.ANALYSIS_PATH.read_bytes()).hexdigest(),
        'items': reviews,
        'validationErrors': errors,
        'result': 'FAIL' if errors else 'PASS_WITH_HISTORICAL_REVIEW_REQUIRED',
    }
    engine.write_json(engine.DATA_ROOT / 'historical-reference-review.json', report)
    print(report['result'], 'retained:', len(reviews), 'errors:', len(errors))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
