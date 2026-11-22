import os
import re
import tempfile
import unittest
from pathlib import Path

import yaml

from physics_studio.metadata import MetadataError, parse_quarto_yaml
from physics_studio.safety import risky_markup, sanitize_generated_qmd
from physics_studio.staging import StagingError, stage_zip
from tests.support import CHAPTER, png_bytes, zip_bytes


class MetadataTests(unittest.TestCase):
    def test_honors_author_lang_cover_and_epub_fields(self):
        meta = parse_quarto_yaml(
            """
book:
  title: Measurement
  author:
    - name: Sugeng Riyanto
  subtitle: Grade 9
lang: id
format:
  epub:
    publisher: Physics Textbook Studio
    cover-image: images/cover.png
    identifier: urn:isbn:9780000000001
    description: Sample chapter
    rights: Copyright 2026
    date: "2026-11-22"
"""
        )
        self.assertEqual(meta.title, "Measurement")
        self.assertEqual(meta.author, "Sugeng Riyanto")
        self.assertEqual(meta.lang, "id")
        self.assertEqual(meta.cover_image, "images/cover.png")
        self.assertEqual(meta.publisher, "Physics Textbook Studio")
        self.assertEqual(meta.identifier, "urn:isbn:9780000000001")
        self.assertEqual(meta.date, "2026-11-22")

    def test_unquoted_title_is_not_dropped(self):
        meta = parse_quarto_yaml("book:\n  title: Motion in a Circle\nauthor: A. Author\n")
        self.assertEqual(meta.title, "Motion in a Circle")
        self.assertEqual(meta.author, "A. Author")

    def test_defaults_match_the_original_worker(self):
        meta = parse_quarto_yaml("project:\n  type: book\n")
        self.assertEqual(meta.title, "Physics Textbook Studio")
        self.assertEqual(meta.author, "Academic Physics Publishing Team")
        self.assertEqual(meta.lang, "id")

    def test_theme_is_limited_to_known_names(self):
        self.assertEqual(parse_quarto_yaml("bc-theme: classic\n").theme, "classic")
        self.assertEqual(parse_quarto_yaml("book:\n  theme: STUDIO\n").theme, "studio")
        self.assertEqual(parse_quarto_yaml("bc-theme: '#evil'\n").theme, "")

    def test_invalid_yaml_is_rejected(self):
        with self.assertRaises(MetadataError):
            parse_quarto_yaml("book: [\n")


class SafetyTests(unittest.TestCase):
    def test_fenced_divs_are_allowed_and_raw_typst_is_not(self):
        self.assertFalse(risky_markup("::: {.givens}\nGiven.\n:::\n"))
        self.assertTrue(risky_markup("```{=typst}\n#circle()\n```\n"))
        self.assertTrue(risky_markup("{{< video >}}\n"))
        cleaned = sanitize_generated_qmd("```{=typst}\n#circle()\n```\n\n::: {.exam-trap}\nTrap.\n:::\n")
        self.assertFalse(risky_markup(cleaned))
        self.assertIn("exam-trap", cleaned)


class StagingTests(unittest.TestCase):
    def stage(self, files: dict) -> Path:
        self.addCleanup(lambda: None)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        work = Path(directory.name)
        stage_zip(zip_bytes(files), work)
        return work

    def test_keeps_images_and_does_not_require_flipbook_qmd(self):
        work = self.stage(
            {
                "bab-01.qmd": CHAPTER,
                "images/vernier.png": png_bytes(),
                "images/units.svg": '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"></svg>',
                "styles/extra.css": ".note { color: #0F2942; }",
                "_quarto.yml": "book:\n  title: Measurement\n  author: Sugeng Riyanto\nlang: id\n",
            }
        )
        self.assertTrue((work / "images/vernier.png").is_file())
        self.assertTrue((work / "images/units.svg").is_file())
        self.assertTrue((work / "gold-boxes.lua").is_file())
        self.assertTrue((work / "index.qmd").is_file())
        config = yaml.safe_load((work / "_quarto.yml").read_text(encoding="utf-8"))
        self.assertEqual(config["book"]["author"], "Sugeng Riyanto")
        self.assertEqual(config["lang"], "id")
        self.assertIn("styles/extra.css", config["format"]["html"]["css"])
        self.assertFalse(config["execute"]["enabled"])
        self.assertNotIn("flipbook", config["book"]["chapters"])

    def test_old_flipbook_shortcodes_do_not_reject_a_pdf_bundle(self):
        work = self.stage(
            {
                "bab-2.qmd": "# Forces\n\nA force has direction.\n",
                "flipbook/flipbook.qmd": "---\nformat: revealjs\n---\n\n{{< video >}}\n",
            }
        )
        self.assertTrue((work / "bab-2.qmd").is_file())
        self.assertFalse((work / "flipbook/flipbook.qmd").exists())

    def test_rejects_path_escape_scripted_svg_and_raw_typst(self):
        with self.assertRaises(StagingError):
            self.stage({"bab-01.qmd": "# A\n", "images/../../secret.png": png_bytes()})
        with self.assertRaises(StagingError):
            self.stage(
                {
                    "bab-01.qmd": "# A\n",
                    "images/bad.svg": '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
                }
            )
        with self.assertRaises(StagingError):
            self.stage({"bab-01.qmd": "```{=typst}\n#circle()\n```\n"})
        with self.assertRaises(StagingError):
            self.stage({"bab-01.qmd": "---\ntitle: Hidden\n---\n\n# A\n"})


class TextbookStagingTests(unittest.TestCase):
    def stage(self, files: dict, env: dict | None = None) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        work = Path(directory.name) / "work"
        saved = {key: os.environ.get(key) for key in ("PHYSICS_FONT_DIR", "PHYSICS_THEME")}
        try:
            for key in saved:
                os.environ.pop(key, None)
            os.environ.update(env or {})
            stage_zip(zip_bytes(files), work)
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        return work

    def test_textbook_filters_run_before_the_box_filter(self):
        work = self.stage({"bab-01.qmd": "# Gerak\n\nTeks.\n"}, {"PHYSICS_FONT_DIR": "/nonexistent"})
        config = yaml.safe_load((work / "_quarto.yml").read_text(encoding="utf-8"))
        self.assertEqual(config["filters"], ["textbook.lua", "gold-boxes.lua"])
        self.assertEqual(config["bc-theme"], "studio")
        self.assertTrue(config["crossref"]["chapters"])
        self.assertIn("textbook.css", config["format"]["html"]["css"])
        self.assertIn("textbook.css", config["format"]["epub"]["css"])
        self.assertNotIn("font-paths", config["format"]["typst"])
        for name in ("textbook.lua", "gold-boxes.lua", "typst-show.typ", "textbook.css"):
            self.assertTrue((work / name).is_file(), name)

    def test_theme_from_yaml_and_worker_default(self):
        work = self.stage({"bab-01.qmd": "# A\n", "_quarto.yml": "bc-theme: classic\n"})
        self.assertEqual(yaml.safe_load((work / "_quarto.yml").read_text())["bc-theme"], "classic")
        work = self.stage({"bab-01.qmd": "# A\n"}, {"PHYSICS_THEME": "classic"})
        self.assertEqual(yaml.safe_load((work / "_quarto.yml").read_text())["bc-theme"], "classic")

    def test_font_dir_is_linked_for_typst_and_embedded_for_html(self):
        fonts = tempfile.TemporaryDirectory()
        self.addCleanup(fonts.cleanup)
        (Path(fonts.name) / "SourceSans3-Regular.woff2").write_bytes(b"wOF2")
        work = self.stage({"bab-01.qmd": "# A\n"}, {"PHYSICS_FONT_DIR": fonts.name})
        config = yaml.safe_load((work / "_quarto.yml").read_text(encoding="utf-8"))
        self.assertEqual(config["format"]["typst"]["font-paths"], ["_fonts"])
        self.assertTrue((work / "_fonts").is_symlink())
        self.assertEqual(config["format"]["html"]["css"][0], "textbook-fonts.css")
        css = (work / "textbook-fonts.css").read_text(encoding="utf-8")
        self.assertIn('url("_fonts/SourceSans3-Regular.woff2") format("woff2")', css)
        self.assertNotIn("textbook-fonts.css", config["format"]["epub"]["css"])

    def test_typst_template_has_no_unescaped_pandoc_dollars(self):
        from physics_studio.staging import ASSETS

        text = (ASSETS / "typst-show.typ").read_text(encoding="utf-8")
        stripped = re.sub(r"\$\$|\$(?:if|endif|else|for|endfor|sep)\b[^$]*\$|\$[a-z.-]+\$", "", text)
        self.assertNotIn("$", stripped)


if __name__ == "__main__":
    unittest.main()
