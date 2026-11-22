"""Every palette must pass WCAG AA for each colour pair the templates draw.

Run with -v to see the logged contrast table. The image build runs the test
suite, so a palette that falls short fails the build.
"""

from __future__ import annotations

import re
import tempfile
import unittest
import zipfile
import io
from pathlib import Path

from physics_studio import palettes
from physics_studio.palettes import CONTRAST_RULES, PALETTES, contrast, contrast_table, failures

ASSETS = Path(__file__).resolve().parents[1] / "physics_studio" / "assets"


class ContrastMathTests(unittest.TestCase):
    def test_reference_values(self):
        self.assertAlmostEqual(contrast("#000000", "#FFFFFF"), 21.0, places=2)
        self.assertAlmostEqual(contrast("#FFFFFF", "#FFFFFF"), 1.0, places=2)
        self.assertAlmostEqual(contrast("#767676", "#FFFFFF"), 4.54, places=2)


class PaletteContrastTests(unittest.TestCase):
    def test_at_least_seven_palettes_and_a_dark_one(self):
        self.assertGreaterEqual(len(PALETTES), 8)
        self.assertIn(palettes.DEFAULT_PALETTE, PALETTES)
        self.assertTrue(palettes.SCREEN_ONLY & set(PALETTES))

    def test_every_palette_defines_every_role(self):
        roles = set(PALETTES[palettes.DEFAULT_PALETTE])
        used = {role for fg, bg, _, _ in CONTRAST_RULES for role in (fg, bg)}
        self.assertLessEqual(used, roles)
        for name, palette in PALETTES.items():
            self.assertEqual(set(palette), roles, name)
            for role, value in palette.items():
                self.assertRegex(value, r"^#[0-9A-F]{6}$", f"{name}.{role}")

    def test_wcag_aa_for_every_pair(self):
        problems: list[str] = []
        for name in PALETTES:
            rows = contrast_table(name)
            print(f"\n[{name}]")
            for fg, bg, ratio, need, usage in rows:
                mark = "ok " if ratio >= need else "FAIL"
                print(f"  {mark} {fg:>12} on {bg:<12} {ratio:5.2f} (min {need}) {usage}")
            problems += failures(name)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_light_text_never_on_light_fill(self):
        # Soft fills always carry dark text in light palettes (and the reverse in dark ones).
        for name, p in PALETTES.items():
            dark = name in palettes.SCREEN_ONLY
            for soft in ("primary-soft", "blue-soft", "blue-softer", "green-soft", "purple-soft", "red-soft", "grey-soft", "surface"):
                fill, ink = palettes.luminance(p[soft]), palettes.luminance(p["ink"])
                self.assertTrue(fill < ink if dark else fill > ink, f"{name}: {soft}")


class PaletteOutputTests(unittest.TestCase):
    def test_typst_and_css_outputs(self):
        for name in PALETTES:
            typ = palettes.typst_dict(name)
            self.assertIn(f'#let bc-palette-name = "{name}"', typ)
            self.assertNotIn("$", typ)  # the partial is a pandoc template
            css = palettes.css_vars(name)
            self.assertIn(f"--bc-primary: {PALETTES[name]['primary']};", css)
        self.assertIn("--bc-deep: #fff", palettes.css_vars("dark"))

    def test_resolve(self):
        self.assertEqual(palettes.resolve("TEAL"), "teal")
        self.assertEqual(palettes.resolve("nope"), "studio")
        self.assertEqual(palettes.resolve("", "classic"), "classic")

    def test_docx_uses_light_palette_for_dark(self):
        self.assertEqual(palettes.docx_palette("dark")["paper"], "FFFFFF")

    def test_template_has_one_replaceable_palette_block(self):
        text = (ASSETS / "typst-show.typ").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"// <bc-palette>.*?// </bc-palette>", text, re.DOTALL)), 1)
        # No raw colour literals outside the palette block: all colour comes from roles.
        outside = re.sub(r"// <bc-palette>.*?// </bc-palette>", "", text, flags=re.DOTALL)
        self.assertEqual(re.findall(r'rgb\("#', outside), [])
        self.assertEqual(re.findall(r"fill: white\b(?!\.)", outside), [])

    def test_css_has_no_hard_coded_text_colours(self):
        text = (ASSETS / "textbook.css").read_text(encoding="utf-8")
        body = text.split("}", 1)[1]  # skip the :root defaults
        self.assertEqual(re.findall(r"(?<![-\w])color:\s*#", body), [])
        self.assertNotIn("#fff;", body)


class PaletteStagingTests(unittest.TestCase):
    def _stage(self, yaml_text: str, env: dict | None = None) -> Path:
        import os
        from unittest import mock

        from physics_studio.staging import stage_zip

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("_quarto.yml", yaml_text)
            z.writestr("bab-01.qmd", "# Motion\n\nText.\n")
        work = Path(tempfile.mkdtemp()) / "w"
        with mock.patch.dict(os.environ, env or {}, clear=False):
            stage_zip(buf.getvalue(), work)
        return work

    def test_palette_from_yaml_is_written_everywhere(self):
        work = self._stage("book:\n  title: T\nbc-palette: teal\n")
        self.assertIn('bc-palette-name = "teal"', (work / "typst-show.typ").read_text())
        self.assertIn(PALETTES["teal"]["primary"], (work / "textbook-palette.css").read_text())
        config = (work / "_quarto.yml").read_text()
        self.assertIn("bc-palette: teal", config)
        self.assertIn("textbook-palette.css", config)

    def test_env_default_and_dark_html_theme(self):
        work = self._stage("book:\n  title: T\n", {"PHYSICS_PALETTE": "dark"})
        config = (work / "_quarto.yml").read_text()
        self.assertIn("bc-palette: dark", config)
        self.assertIn("theme: darkly", config)

    def test_classic_theme_defaults_to_classic_palette(self):
        work = self._stage("book:\n  title: T\nbc-theme: classic\n", {"PHYSICS_PALETTE": ""})
        self.assertIn("bc-palette: classic", (work / "_quarto.yml").read_text())


if __name__ == "__main__":
    unittest.main()
