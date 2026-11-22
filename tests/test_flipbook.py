import tempfile
import unittest
from pathlib import Path

from physics_studio.flipbook import flipbook_html
from physics_studio.render import combine_book_html


class FlipbookTests(unittest.TestCase):
    def test_pages_are_embedded_and_there_is_no_slide_runtime(self):
        html = flipbook_html("Measurement", [b"\xff\xd8\xff\xd9", b"\xff\xd8\xff\xd9"], lang="id")
        self.assertIn('data-page-count="2"', html)
        self.assertEqual(html.count("data:image/jpeg;base64,"), 2)
        self.assertIn("Next page", html)
        self.assertIn('lang="id"', html)
        self.assertNotIn("reveal", html.lower())
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)


class CombineHtmlTests(unittest.TestCase):
    def test_joins_book_pages_and_retargets_links(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root))
        (root / "index.html").write_text(
            '<html><head><title>Book</title></head><body><a href="./bab-01.html">next</a>'
            '<main id="quarto-content"><p>Preface</p></main></body></html>',
            encoding="utf-8",
        )
        (root / "bab-01.html").write_text(
            '<html><head><title>Chapter</title></head><body><a href="index.html">home</a>'
            "<main><p>Vernier caliper</p></main></body></html>",
            encoding="utf-8",
        )
        combined = combine_book_html(root)
        self.assertIn("Preface", combined)
        self.assertIn("Vernier caliper", combined)
        self.assertIn('href="#part-bab-01"', combined)
        self.assertNotRegex(combined, r'href="[^"]+\.html')
        # One <main>: several would overlap in Quarto's grid layout.
        self.assertEqual(combined.count("<main"), 1)
        self.assertEqual(combined.count("</main>"), 1)
        self.assertIn('<section id="part-bab-01" class="book-part">', combined)


if __name__ == "__main__":
    unittest.main()
