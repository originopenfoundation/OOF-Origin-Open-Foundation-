from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("submit_indexnow", ROOT / "tools" / "submit_indexnow.py")
assert SPEC and SPEC.loader
INDEXNOW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INDEXNOW)


class IndexNowTests(unittest.TestCase):
    def test_published_key_file_matches_workflow_key(self) -> None:
        key = "6ff7528f813141d19583be3c43890829"
        self.assertTrue(INDEXNOW.key_file_is_valid(key))
        self.assertEqual(
            INDEXNOW.key_location_for(key),
            "https://originopenfoundation.org/6ff7528f813141d19583be3c43890829.txt",
        )

    def test_sitemap_urls_are_canonical_and_nonempty(self) -> None:
        urls = INDEXNOW.read_sitemap_urls()
        self.assertGreater(len(urls), 0)
        self.assertTrue(all(url.startswith("https://originopenfoundation.org/") for url in urls))


if __name__ == "__main__":
    unittest.main()
