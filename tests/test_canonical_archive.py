import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("archive", ROOT / "tools" / "oof_canonical_archive.py")
archive = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(archive)


class CanonicalArchiveTests(unittest.TestCase):
    def test_inventory_has_stable_unique_ids(self):
        objects = archive.inventory()
        ids = [item["objectId"] for item in objects]
        self.assertGreater(len(ids), 100)
        self.assertEqual(len(ids), len(set(ids)))

    def test_package_hashes_and_comparison(self):
        objects = archive.inventory()[:3]
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            reference = archive.create_package(objects, base / "reference", "test")
            self.assertTrue(archive.verify(reference))
            current = archive.create_package(objects, base / "current", "test")
            target = current / "content" / objects[0]["path"]
            target.write_text(target.read_text(encoding="utf-8", errors="replace") + "\nchange", encoding="utf-8")
            index = json.loads((current / "index.json").read_text(encoding="utf-8"))
            index[0]["sha256"] = archive.sha256_file(target)
            archive.write_json(current / "index.json", index)
            report_path = archive.compare(reference, current)
            report = json.loads(report_path.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "REVIEW REQUIRED")
            self.assertIn(objects[0]["objectId"], report["modified"])

    def test_comparison_detects_missing_object(self):
        objects = archive.inventory()[:3]
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            reference = archive.create_package(objects, base / "reference", "test")
            current = archive.create_package(objects[1:], base / "current", "test")
            report_path = archive.compare(reference, current)
            report = json.loads(report_path.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertIn(objects[0]["objectId"], report["missing"])
            self.assertEqual(report["status"], "REVIEW REQUIRED")

    def test_comparison_reports_new_object_without_corruption(self):
        objects = archive.inventory()[:3]
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            reference = archive.create_package(objects[:2], base / "reference", "test")
            current = archive.create_package(objects, base / "current", "test")
            report_path = archive.compare(reference, current)
            report = json.loads(report_path.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertIn(objects[2]["objectId"], report["new"])
            self.assertEqual(report["modified"], [])
            self.assertEqual(report["missing"], [])
            self.assertEqual(report["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
