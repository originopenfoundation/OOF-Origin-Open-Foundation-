import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import audit_discovery_infrastructure as audit
import build_ai_compatibility as build
import oof_canonical_archive as archive
import validate_ai_compatibility as validate


class AnalyticsDiscoveryTests(unittest.TestCase):
    def test_admin_is_not_public_discovery_content(self):
        for module in (audit, build, validate):
            self.assertNotIn(ROOT / 'analytics-admin' / 'index.html', module.public_pages())
        self.assertIn('analytics-admin', archive.PUBLIC_EXCLUDES)


if __name__ == '__main__':
    unittest.main()
