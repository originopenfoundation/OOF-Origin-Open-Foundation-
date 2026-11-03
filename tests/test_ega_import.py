import re
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class EgaImportTests(unittest.TestCase):
    def test_all_standard_module_links_exist(self):
        directory = ROOT / 'content' / 'ega'
        index = (directory / 'ega-complete-index.html').read_text(encoding='utf-8')
        links = re.findall(r'href="(ega-[^"]+\.html)#(module-[^"]+)"', index)
        self.assertEqual(len(links), 65)
        self.assertEqual(set(Counter(path for path, _ in links).values()), {5})
        for filename, anchor in links:
            self.assertIn(f'id="{anchor}"', (directory / filename).read_text(encoding='utf-8'))
        self.assertNotIn('— Core Module', index)

    def test_private_email_envelope_not_published(self):
        paths = list((ROOT / 'content' / 'ega').glob('*.html'))
        paths.append(ROOT / 'content' / 'a' / 'oof-authority-enforcement-boundary-reference.html')
        for path in paths:
            source = path.read_text(encoding='utf-8').lower()
            for private in ('samuel.malicky', 'swissstaffingagency', 'knowenger@gmail', 'mail.google.com', 'gutflex@gmail'):
                self.assertNotIn(private, source, str(path))

    def test_reference_image_and_navigation(self):
        page = (ROOT / 'content' / 'a' / 'oof-authority-enforcement-boundary-reference.html').read_text(encoding='utf-8')
        image = 'oof-authority-enforcement-boundary-reference.png'
        self.assertIn(image, page)
        self.assertTrue((ROOT / 'assets' / 'images' / image).is_file())
        header = (ROOT / 'header.html').read_text(encoding='utf-8')
        self.assertIn('content/ega/ega-complete-index.html', header)
        self.assertIn('content/a/oof-authority-enforcement-boundary-reference.html', header)


if __name__ == '__main__':
    unittest.main()
