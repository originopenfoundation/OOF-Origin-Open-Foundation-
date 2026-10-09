"""Guard localized access pages and their canonical English boundaries."""

import json
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_localization as localization
import build_ai_compatibility as discovery
import validate_ai_compatibility as validator


class PageLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []
        self.ids = []
        self.alternates = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.append(attrs["id"])
        if tag in {"a", "link", "script"}:
            target = attrs.get("src") or attrs.get("href")
            if target:
                self.targets.append(target)
        if tag == "link" and attrs.get("hreflang"):
            self.alternates[attrs["hreflang"]] = attrs["href"]


class LocalizationTests(unittest.TestCase):
    def test_italian_and_arabic_metadata_assets_and_search(self):
        search = json.loads((ROOT / "search-index.json").read_text(encoding="utf-8"))
        for prefix, code, locale, native in [("it", "it-IT", "it_IT", "Italiano"), ("ar", "ar", "ar_AR", "العربية")]:
            with self.subTest(language=prefix):
                source = (ROOT / prefix / "index.html").read_text(encoding="utf-8")
                self.assertIn('lang="' + code + '"', source)
                self.assertIn('property="og:locale" content="' + locale + '"', source)
                self.assertIn('href="../index.html" hreflang="en"', source)
                self.assertNotIn("\ufffd", source)
                for term in ("OOF®", "Structured Reality™", "UCL™", "Global AI Incident Intelligence™"):
                    self.assertIn(term, source)
                parser = PageLinks()
                parser.feed(source)
                self.assertEqual(len(parser.ids), len(set(parser.ids)))
                for target in parser.targets:
                    parsed = urlparse(target)
                    if not parsed.scheme and not parsed.netloc and parsed.path:
                        self.assertTrue((ROOT / prefix / unquote(parsed.path)).resolve().exists(), target)
                entry = next(item for item in search if item["url"] == prefix + "/index.html")
                self.assertIn(native, entry["title"])

    def test_arabic_rtl_and_protected_name_isolation(self):
        source = (ROOT / "ar/index.html").read_text(encoding="utf-8")
        self.assertIn('<html lang="ar" dir="rtl">', source)
        self.assertIn('<bdi dir="ltr">Structured Reality™</bdi>', source)
        self.assertIn('<bdi dir="ltr">OOF®</bdi>', source)
        italian = (ROOT / "it/index.html").read_text(encoding="utf-8")
        self.assertNotIn('dir="rtl"', italian)


    def test_russian_discovery_and_canonical_boundary(self):
        source = (ROOT / "ru/index.html").read_text(encoding="utf-8")
        self.assertIn('<html lang="ru-RU">', source)
        self.assertIn('property="og:locale" content="ru_RU"', source)
        self.assertIn('href="../index.html" hreflang="en"', source)
        self.assertNotIn("\ufffd", source)
        self.assertIn("Русский", source)
        for term in ("OOF®", "Structured Reality™", "UCL™", "Global AI Incident Intelligence™"):
            self.assertIn(term, source)
        parser = PageLinks()
        parser.feed(source)
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        for target in parser.targets:
            parsed = urlparse(target)
            if not parsed.scheme and not parsed.netloc and parsed.path:
                self.assertTrue((ROOT / "ru" / unquote(parsed.path)).resolve().exists(), target)
        search = json.loads((ROOT / "search-index.json").read_text(encoding="utf-8"))
        entry = next(item for item in search if item["url"] == "ru/index.html")
        self.assertIn("Русский", entry["title"])
        self.assertIn("целостность", entry["text"])

    def test_language_registries_agree(self):
        expected = {prefix: details["code"] for prefix, details in localization.LANGUAGES.items()}
        self.assertEqual(expected, validator.LOCALIZED_LANGUAGES)
        self.assertEqual(expected, {prefix: value[0] for prefix, value in discovery.LOCALIZED_LANGUAGES.items()})
        policy = json.loads((ROOT / "data/localization/localization-policy.json").read_text(encoding="utf-8"))
        self.assertEqual(expected, {item["prefix"]: item["code"] for item in policy["languages"]})
        self.assertEqual(policy["canonicalMethodologyLanguage"], "en")
        self.assertEqual(policy["translatedPublicPages"], ["index.html"])

    def test_all_translations_preserve_german_content_topology(self):
        reference = localization.TRANSLATIONS["de"]
        for prefix, translation in localization.TRANSLATIONS.items():
            with self.subTest(language=prefix):
                self.assertEqual(set(translation), set(reference))
                self.assertEqual(len(translation["sections"]), len(reference["sections"]))
                for (_, blocks), (_, expected) in zip(translation["sections"], reference["sections"]):
                    self.assertEqual(len(blocks), len(expected))
                    for block, reference_block in zip(blocks, expected):
                        self.assertEqual(isinstance(block, list), isinstance(reference_block, list))
                        if isinstance(block, list):
                            self.assertEqual(len(block), len(reference_block))

    def test_home_pages_have_reciprocal_language_alternates(self):
        expected = dict(discovery.localized_home_alternates("index.html"))
        for relative in ["index.html", *[f"{prefix}/index.html" for prefix in localization.LANGUAGES]]:
            with self.subTest(page=relative):
                parser = PageLinks()
                parser.feed((ROOT / relative).read_text(encoding="utf-8"))
                self.assertEqual(parser.alternates, expected)

    def test_korean_links_assets_and_section_anchors_resolve(self):
        page = ROOT / "ko/index.html"
        parser = PageLinks()
        parser.feed(page.read_text(encoding="utf-8"))
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        for target in parser.targets:
            parsed = urlparse(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            resolved = (page.parent / unquote(parsed.path)).resolve()
            self.assertTrue(resolved.exists(), target)

    def test_korean_discovery_search_and_canonical_boundary(self):
        page = (ROOT / "ko/index.html").read_text(encoding="utf-8")
        self.assertIn('<html lang="ko-KR">', page)
        self.assertIn('property="og:locale" content="ko_KR"', page)
        self.assertIn('rel="canonical" href="https://originopenfoundation.org/ko/"', page)
        self.assertIn('href="../index.html" hreflang="en"', page)
        for term in ("OOF®", "OriginOpen® Foundation", "Structured Reality™", "UCL™", "Global AI Incident Intelligence™"):
            self.assertIn(term, page)
        self.assertNotIn("\ufffd", page)
        self.assertRegex(page, r"[가-힣]")
        schemas = re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
        self.assertEqual(json.loads(schemas[0])["inLanguage"], "ko-KR")
        search = json.loads((ROOT / "search-index.json").read_text(encoding="utf-8"))
        entry = next(item for item in search if item["url"] == "ko/index.html")
        self.assertIn("한국어", entry["title"])
        self.assertIn("상호 운용", entry["text"])
        sitemap = ET.parse(ROOT / "sitemap.xml")
        urls = {element.text for element in sitemap.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")}
        self.assertIn("https://originopenfoundation.org/ko/", urls)


if __name__ == "__main__":
    unittest.main()
