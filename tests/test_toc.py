import unittest
from pathlib import Path

from physics_studio.generator.qmd import units_for
from physics_studio.generator.toc import TocError, find_book, find_chapter, parse_toc

TOC = Path("fixtures/master_toc.txt").read_text(encoding="utf-8")


class TocTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.toc = parse_toc(TOC)

    def test_all_six_books(self):
        self.assertEqual([book["id"] for book in self.toc["books"]], ["A0", "A1", "B1", "B2", "C1", "C2"])
        pages = {book["id"]: book["pages"] for book in self.toc["books"]}
        self.assertEqual(pages, {"A0": 450, "A1": 450, "B1": 460, "B2": 480, "C1": 460, "C2": 480})

    def test_series_a_has_numbered_subsections(self):
        book = find_book(self.toc, "A0")
        chapter = find_chapter(book, 1)
        self.assertEqual(chapter["pages"], 40)
        self.assertEqual(chapter["title"], "Physical Quantities, Measurement Techniques & Experimental Skills")
        numbers = [item["number"] for item in chapter["subsections"]]
        self.assertEqual(numbers, ["1.1", "1.2", "1.3", "1.4", "1.5"])
        self.assertTrue(chapter["subsections"][0]["title"].startswith("SI Base"))
        self.assertEqual(len(book["chapters"]), 10)
        matter = (book["front_matter"]["pages"] if book["front_matter"] else 0) + sum(
            item["pages"] for item in book["back_matter"]
        )
        self.assertEqual(matter + sum(item["pages"] for item in book["chapters"]), 450)

    def test_series_a1_includes_chapter_zero(self):
        chapter = find_chapter(find_book(self.toc, "Book A1"), 0)
        self.assertEqual([item["number"] for item in chapter["subsections"]], ["0.1", "0.2", "0.3", "0.4"])

    def test_series_b_and_c_keep_notes_on_the_chapter_line(self):
        b1 = find_chapter(find_book(self.toc, "B1"), 1)
        self.assertEqual(b1["pages"], 35)
        self.assertEqual(b1["subsections"], [])
        self.assertIn("AS Topic 1", b1["notes"])
        self.assertEqual(len(find_book(self.toc, "B1")["chapters"]), 11)
        self.assertEqual(len(find_book(self.toc, "B2")["chapters"]), 12)
        c1 = find_chapter(find_book(self.toc, "C1"), 1)
        self.assertIn("Theme A.1", c1["title"])
        self.assertEqual(c1["subsections"], [])
        self.assertIn("Projectile", c1["notes"])
        self.assertEqual(len(find_book(self.toc, "C1")["chapters"]), 10)
        self.assertEqual(len(find_book(self.toc, "C2")["chapters"]), 9)
        self.assertIn("Theme A.5", find_chapter(find_book(self.toc, "c2"), 1)["title"])

    def test_front_and_back_matter(self):
        book = find_book(self.toc, "A0")
        self.assertEqual(book["front_matter"]["pages"], 12)
        self.assertEqual(book["back_matter"][0]["pages"], 35)
        self.assertTrue(book["curriculum"].startswith("Indonesian"))

    def test_units_follow_the_two_patterns(self):
        a0 = find_chapter(find_book(self.toc, "A0"), 1)
        units = units_for(a0)
        self.assertEqual(len(units), 7)
        self.assertEqual(sum(unit.words for unit in units), a0["pages"] * 320)
        b1 = find_chapter(find_book(self.toc, "B1"), 1)
        modules = units_for(b1)
        self.assertEqual(len(modules), 10)
        self.assertEqual(sum(unit.words for unit in modules), b1["pages"] * 320)

    def test_unknown_book(self):
        with self.assertRaises(TocError):
            find_book(self.toc, "Z9")


if __name__ == "__main__":
    unittest.main()
