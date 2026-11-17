import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DWAGA = ROOT / 'content' / 'dwaga'


class LinksAndIds(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.append(attrs['id'])
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])


class DwagaContentTests(unittest.TestCase):
    def test_module_links_resolve_to_unique_module_sections(self):
        index = LinksAndIds()
        index.feed((DWAGA / 'dwaga-complete-index.html').read_text(encoding='utf-8'))
        links = [link for link in index.links if '#module-' in link]
        self.assertEqual(len(links), 40)
        self.assertEqual(len(set(links)), 40)
        for link in links:
            filename, fragment = link.split('#', 1)
            page = LinksAndIds()
            page.feed((DWAGA / filename).read_text(encoding='utf-8'))
            self.assertEqual(page.ids.count(fragment), 1, link)

    def test_source_emails_are_not_published(self):
        pages = list(DWAGA.glob('*.html'))
        self.assertEqual(len(pages), 12)
        for page in pages:
            self.assertNotRegex(page.read_text(encoding='utf-8'), r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', page.name)

    def test_index_uses_names_from_individual_standards(self):
        index = (DWAGA / 'dwaga-complete-index.html').read_text(encoding='utf-8')
        for name in ('RIBM — Representation &amp; Interpretation Binding Module',
                     'HCEM — Handover Completeness &amp; Exceptions Module',
                     'DOVIM — Delivered Object Version Identification Module'):
            self.assertIn(name, index)
        self.assertNotIn('RIBM — Receipt Identification &amp; Boundary Module', index)


if __name__ == '__main__':
    unittest.main()
