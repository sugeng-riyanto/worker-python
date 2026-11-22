"""Lua filter tests. They need Pandoc (from Quarto or PATH) and are skipped without it."""

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "physics_studio" / "assets"


def _pandoc() -> list[str] | None:
    quarto = os.environ.get("QUARTO_PATH") or shutil.which("quarto")
    if quarto:
        return [quarto, "pandoc"]
    pandoc = shutil.which("pandoc")
    return [pandoc] if pandoc else None


PANDOC = _pandoc()


def run(markdown: str, to: str, lang: str | None = "id") -> str:
    proc = subprocess.run(
        [
            *PANDOC,
            "-f",
            "markdown",
            "-t",
            to,
            "--wrap=none",
            *(["-M", f"lang={lang}"] if lang else []),
            "-L",
            str(ASSETS / "textbook.lua"),
            "-L",
            str(ASSETS / "gold-boxes.lua"),
        ],
        input=markdown,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def ast(markdown: str) -> dict:
    return json.loads(run(markdown, "json"))


def kinds(node, found=None):
    """Collect (type, classes) for every Div in a Pandoc JSON tree."""
    found = [] if found is None else found
    if isinstance(node, dict):
        if node.get("t") == "Div":
            found.append(node["c"][0][1])
        for value in node.values():
            kinds(value, found)
    elif isinstance(node, list):
        for value in node:
            kinds(value, found)
    return found


@unittest.skipUnless(PANDOC, "pandoc is not available")
class MathRescueTests(unittest.TestCase):
    def test_escaped_dollars_from_google_docs_become_math(self):
        out = run(r"Speed is \$v = s / t\$ and \$a = \\Delta v / \\Delta t\$." + "\n", "latex")
        self.assertIn(r"\(v = s / t\)", out)
        self.assertIn(r"\(a = \Delta v / \Delta t\)", out)
        self.assertNotIn(r"\$", out)

    def test_display_math_and_money_are_handled(self):
        out = run(r"\$\$E = mc^2\$\$" + "\n\nIt costs \\$5 and \\$10 today.\n", "latex")
        self.assertIn(r"\[E = mc^2\]", out)
        self.assertIn(r"\$5 and \$10", out)


@unittest.skipUnless(PANDOC, "pandoc is not available")
class HeadingTests(unittest.TestCase):
    def test_chapter_and_module_prefixes_are_removed(self):
        out = run(
            "# CHAPTER 2: KINEMATICS --- MOTION IN ONE & TWO DIMENSIONS\n\n"
            "## MODULE 8: END-OF-SUB-SECTION CHECKPOINT\n\n"
            "## 2.1 Speed, Velocity & Uniform Acceleration\n\n"
            "## MODULE 1: CHAPTER OPENER & OBJECTIVES MATRIX\n",
            "markdown",
        )
        self.assertIn("# Kinematics --- Motion in One & Two Dimensions ", out)
        self.assertRegex(out, r"## End-of-sub-section Checkpoint \{[^}]*\.unnumbered\}")
        self.assertIn("## Speed, Velocity & Uniform Acceleration", out)
        self.assertNotIn("CHAPTER OPENER", out.upper())


@unittest.skipUnless(PANDOC, "pandoc is not available")
class StructureRecoveryTests(unittest.TestCase):
    DRAFT = (
        "### Sub-Section Pedagogical Header\n\n- **Ideal Duration:** 90 Minutes\n\n"
        "### Coherent Prose (1 Paragraph = 1 Idea) & Dual Concrete Examples\n\nSpeed is distance per time.\n\n"
        "> **QR WATCH (`22 mm × 22 mm` Dedicated Slot):**\\\n> `[QR WATCH | Scan for PhET]`\n\n"
        "### G.I.V.E.N.S. A\\* Problem-Solving Protocol & Worked Exemplar 2.2\n\n**Problem:** A train...\n\n"
        "> *★ G.I.V.E.N.S. A PROBLEM-SOLVING PROTOCOL*\n\n> - **G (Given):** 20 m/s\n\n"
        "> **✎ ACTIVE LEARNING WORKSPACE 2.1A --- Acceleration Check**\\\n> A train accelerates.\n\n"
        "> 1.  Change in velocity = ____\n\n"
        "> **Teacher Verification Stamp:** `[ ] L1`\n"
    )

    def test_scaffold_headings_and_quotes_become_boxes(self):
        found = kinds(ast(self.DRAFT))
        flat = {cls for classes in found for cls in classes}
        for kind in ("teacher-note", "qr", "worked-example", "workspace"):
            self.assertIn(kind, flat)
        self.assertNotIn("givens", flat, "a G.I.V.E.N.S. block inside a worked example is unwrapped")
        out = run(self.DRAFT, "markdown")
        self.assertNotIn("Coherent Prose", out)
        self.assertNotIn("Sub-Section Pedagogical Header", out)
        self.assertNotIn("BlockQuote", json.dumps(ast(self.DRAFT)))

    def test_typst_output_calls_template_functions(self):
        out = run(self.DRAFT, "typst")
        self.assertIn('#bc-box(kind: "worked-example", title: [Contoh Soal #bc-number("example")]', out)
        self.assertIn('#bc-aside(kind: "qr", title: [Pindai]', out)
        self.assertIn('#bc-box(kind: "workspace", title: [Acceleration Check]', out)


@unittest.skipUnless(PANDOC, "pandoc is not available")
class BoxRenderingTests(unittest.TestCase):
    def test_explicit_divs_in_each_format(self):
        source = (
            '::: {.objectives}\n- Define speed.\n:::\n\n'
            '::: {.contoh-soal title="Contoh Soal Khusus"}\nA car...\n:::\n\n'
            '::: {.review}\n1. Question\n:::\n\n'
            '::: {.remember}\nUnits!\n:::\n'
        )
        typst = run(source, "typst")
        self.assertIn('#bc-box(kind: "objectives", title: [Dalam subbab ini, kamu akan mempelajari:]', typst)
        self.assertIn('title: [Contoh Soal Khusus], wide: false', typst)
        self.assertIn('#bc-box(kind: "review", title: [Ayo Mengulang], wide: true)', typst)
        self.assertIn('#bc-aside(kind: "remember", title: [Ingat!])', typst)

        html = run(source, "html", lang="en")
        self.assertIn('class="objectives bc-box gold-box-done"', html)
        self.assertIn("In this section, you will learn the following:", html)
        self.assertIn('class="remember bc-aside gold-box-done"', html)
        self.assertIn("bc-numbered-example bc-explicit-title", html)


    def test_long_sidebar_note_moves_into_the_main_column(self):
        long_text = "word " * 120
        typst = run(f"::: {{.quick-check}}\n{long_text}\n:::\n", "typst")
        self.assertNotIn("#bc-aside", typst)
        self.assertIn('#bc-box(kind: "workspace", title: [Cek Cepat]', typst)

    def test_docx_uses_custom_styles(self):
        proc = subprocess.run(
            [*PANDOC, "-f", "markdown", "-t", "docx", "-o", "-", "-L", str(ASSETS / "textbook.lua"), "-L", str(ASSETS / "gold-boxes.lua")],
            input="::: {.practice}\n1. Hitung.\n:::\n".encode("utf-8"),
            capture_output=True,
            check=True,
        )
        import io
        import zipfile

        document = zipfile.ZipFile(io.BytesIO(proc.stdout)).read("word/document.xml").decode("utf-8")
        self.assertIn("BoxPractice", document)



class EnglishDefaultTests(unittest.TestCase):
    def setUp(self):
        if not PANDOC:
            self.skipTest("pandoc not installed")

    def test_labels_are_english_without_lang(self):
        source = "# Motion\n\n::: {.worked-example}\nA car travels.\n:::\n\n::: {.practice}\n1. Try.\n:::\n\n::: {.review}\nQ1\n:::\n"
        typst = run(source, "typst", lang=None)
        self.assertIn("Worked Example", typst)
        self.assertIn("Let's Practise", typst)
        self.assertIn("Let's Review", typst)
        self.assertNotIn("Contoh Soal", typst)

    def test_english_lang_gives_english_labels_and_id_stays_available(self):
        source = "::: {.quick-check}\nWhat is speed?\n:::\n"
        self.assertIn("Quick Check", run(source, "typst", lang="en"))
        self.assertIn("Cek Cepat", run(source, "typst", lang="id"))


if __name__ == "__main__":
    unittest.main()
