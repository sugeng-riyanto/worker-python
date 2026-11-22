"""v14.2: math in every format, justified text, scaffolds, image placeholders,
graph paper, slim single-file HTML. Filter tests need Pandoc (skipped without it);
the full render test needs Quarto with Typst (QUARTO_PATH)."""

import io
import json
import os
import re
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from physics_studio import reference_docx
from physics_studio.render import GOOGLE_FONTS_CSS, slim_html
from tests.test_filters import ASSETS, PANDOC, run, run_binary

TRICKY = r"""
# Forces

Speed $v = 12\,\mathrm{m\,s^{-1}}$, $a = \frac{v-u}{t}$, $\vec{F}_{\text{net}} = m\vec{a}$,
$E_k = \tfrac{1}{2}mv^2$, $T = 2\pi\sqrt{\dfrac{L}{g}}$, $R = 47\,\Omega$, $\theta = 30^\circ$,
$h_{\max}$, $v_0$, $c = 3.00 \times 10^{8}\,\mathrm{m\,s^{-1}}$, $\SI{9.81}{m/s^2}$,
$\SI{20}{\celsius}$, $\qty{5.0}{\kilo\gram}$, $\num{6.02e23}$, $\SI{3}{\metre\per\second}$,
$45\degree$, prose \SI{1.5}{\newton}. Money: \$5 and \$10.

$$
\begin{aligned}
v^2 &= u^2 + 2as \\
s &= ut + \frac{1}{2}at^2
\end{aligned}
$$
"""

# Strings that must never reach a reader: unconverted siunitx, escaped
# delimiters, raw TeX outside math.
LEAKS = [r"\\SI\b", r"\\qty\b", r"\\num\b", r"\\si\b", r"\\celsius", r"\\degree", r"\\\(", r"\\\)", r"\\frac", r"\\mathrm"]


def maths(node, found=None):
    found = [] if found is None else found
    if isinstance(node, dict):
        if node.get("t") == "Math":
            found.append(node["c"][1])
        for value in node.values():
            maths(value, found)
    elif isinstance(node, list):
        for value in node:
            maths(value, found)
    return found


@unittest.skipUnless(PANDOC, "pandoc not available")
class MathTests(unittest.TestCase):
    def test_siunitx_and_macros_are_normalised(self):
        tex = maths(json.loads(run(TRICKY, "json", lang="en")))
        joined = "\n".join(tex)
        for leak in (r"\SI", r"\qty", r"\num", r"\celsius", r"\degree", r"\tfrac"):
            self.assertNotIn(leak, joined)
        self.assertIn(r"9.81\,\mathrm{m/s^2}", joined)
        self.assertIn(r"5.0\,\mathrm{kg}", joined)
        self.assertIn(r"6.02 \times 10^{23}", joined)
        self.assertIn(r"3\,\mathrm{m\,s^{-1}}", joined)
        self.assertIn(r"20\,\mathrm{°C}", joined)
        self.assertIn(r"1.5\,\mathrm{N}", joined)  # \SI in prose becomes math too
        self.assertTrue(any("aligned" in t for t in tex))

    def test_money_is_not_math(self):
        out = run(TRICKY, "plain", lang="en")
        self.assertIn("$5 and $10", out)

    def test_every_format_has_no_tex_leaks(self):
        for to in ("html", "typst", "docx", "epub3"):
            with self.subTest(to=to):
                if to in ("docx", "epub3"):
                    # Write to a file: the quarto pandoc wrapper may append a newline
                    # to binary stdout, which corrupts the zip.
                    with tempfile.TemporaryDirectory() as tmp:
                        target = Path(tmp) / ("out." + to)
                        subprocess.run(
                            [*PANDOC, "-f", "markdown", "-t", to, "-M", "lang=en", "-o", str(target),
                             *(["--mathml"] if to == "epub3" else []),
                             "-L", str(ASSETS / "textbook.lua"), "-L", str(ASSETS / "textbook-extras.lua"),
                             "-L", str(ASSETS / "gold-boxes.lua")],
                            input=TRICKY.encode(), capture_output=True, check=True)
                        archive = zipfile.ZipFile(io.BytesIO(target.read_bytes()))
                    names = [n for n in archive.namelist() if n.endswith((".xhtml", "document.xml"))]
                    text = "".join(archive.read(n).decode("utf-8") for n in names)
                    math_tag = "m:oMath" if to == "docx" else "math"
                    self.assertGreaterEqual(text.count("<" + math_tag), 18)
                    text = re.sub(r"<(m:oMath|math)\b.*?</\1>", "", text, flags=re.S)
                else:
                    text = run(TRICKY, to, lang="en")
                    if to == "html":
                        text = re.sub(r'<span class="math (inline|display)">.*?</span>', "", text, flags=re.S)
                    else:
                        text = re.sub(r"\$[^$]*\$", "", text)  # typst math
                for leak in LEAKS:
                    self.assertIsNone(re.search(leak, text), f"{to}: {leak}")

    def test_docx_equations_round_trip(self):
        """Word equations (OMML) read back as the same TeX."""
        proc = run_binary(
            [*PANDOC, "-f", "markdown", "-t", "docx", "-o", "-", "-L", str(ASSETS / "textbook-extras.lua")],
            input=b"$a = \\frac{v-u}{t}$ and $\\SI{3}{\\metre\\per\\second}$", capture_output=True, check=True)
        back = subprocess.run([*PANDOC, "-f", "docx", "-t", "markdown"], input=proc.stdout, capture_output=True, check=True)
        text = back.stdout.decode()
        self.assertIn(r"\frac{v - u}{t}", text)
        self.assertIn("s^{- 1}", text.replace("s^{-1}", "s^{- 1}"))


@unittest.skipUnless(PANDOC, "pandoc not available")
class ExtrasTests(unittest.TestCase):
    FRAME = '::: {.figure-frame height="50mm" caption="A trolley on a ramp."}\nTrolley, ramp, light gate.\n:::\n'
    GRAPH = ('::: {.graph-paper width="100mm" height="60mm" x-label="t / s" y-label="v / m/s" '
             'x-max="5" y-max="10" points="0,0 1,2 2,4" line="best-fit" caption="Plot v against t."}\n:::\n')

    def test_figure_frame_in_every_format(self):
        typst = run(self.FRAME, "typst", lang="en")
        self.assertIn("#bc-figure-frame(height: 50mm", typst)
        self.assertIn("A trolley on a ramp.", typst)
        html = run(self.FRAME, "html", lang="en")
        self.assertIn('class="bc-figure-frame', html)
        self.assertIn("min-height:50mm", html)
        self.assertIn("Image placeholder", html)
        self.assertIn("Tempat gambar", run(self.FRAME, "html", lang="id"))
        proc = run_binary(
            [*PANDOC, "-f", "markdown", "-t", "docx", "-o", "-", "-L", str(ASSETS / "textbook-extras.lua")],
            input=self.FRAME.encode(), capture_output=True, check=True)
        document = zipfile.ZipFile(io.BytesIO(proc.stdout)).read("word/document.xml").decode()
        self.assertIn('w:val="FigureFrame"', document)
        self.assertGreaterEqual(document.count("<w:p>") + document.count("<w:p "), 6)  # reserved height

    def test_graph_paper_has_minor_and_major_gridlines(self):
        html = run(self.GRAPH, "html", lang="en")
        svg = re.search(r"<svg.*?</svg>", html, re.S).group(0)
        minor = svg.count('stroke-width="0.1"')
        major = svg.count('stroke-width="0.3"')
        # 100 x 60 mm: 101 + 61 lines, every 10th one major
        self.assertEqual(major, 11 + 7)
        self.assertEqual(minor, 101 + 61 - 18)
        self.assertIn('width="118mm"', svg)
        self.assertIn(">t / s<", svg)
        self.assertIn("<path", svg)  # plotted points
        typst = run(self.GRAPH, "typst", lang="en")
        self.assertIn("#bc-graph-paper(width: 90mm, height: 60mm, minor: 1mm, major: 10mm", typst)
        self.assertIn("points: ((0, 0), (1, 2), (2, 4))", typst)
        self.assertIn("fit: (2, 0)", typst)

    def test_graph_paper_is_an_svg_image_in_docx(self):
        proc = run_binary(
            [*PANDOC, "-f", "markdown", "-t", "docx", "-o", "-", "-L", str(ASSETS / "textbook-extras.lua")],
            input=self.GRAPH.encode(), capture_output=True, check=True)
        names = zipfile.ZipFile(io.BytesIO(proc.stdout)).namelist()
        self.assertTrue(any(n.startswith("word/media/") and n.endswith(".svg") for n in names), names)

    def test_scaffolds_render_as_boxes(self):
        kinds = ["guess", "ideal", "cer", "think-pair-share", "concept-map", "estimate-check", "free-body",
                 "data-analysis", "error-analysis", "real-world", "poe", "teacher-verification"]
        md = "\n".join(f"::: {{.{k}}}\nBody {k}.\n:::\n" for k in kinds)
        html = run(md, "html", lang="en")
        for k in kinds:
            self.assertRegex(html, rf'class="{k} bc-box', k)
        for label in ("GUESS: Given", "Claim · Evidence · Reasoning", "Free-Body Diagram", "Teacher Verification", "IDEAL"):
            self.assertIn(label, html)
        typst = run(md, "typst", lang="en")
        template = (ASSETS / "typst-show.typ").read_text(encoding="utf-8")
        css = (ASSETS / "textbook.css").read_text(encoding="utf-8")
        lua = (ASSETS / "gold-boxes.lua").read_text(encoding="utf-8")
        for k in kinds:
            self.assertIn(f'#bc-box(kind: "{k}"', typst)
            self.assertRegex(template, rf'(^|\s)"?{re.escape(k)}"?: \(fill:', k)
            self.assertIn(f".{k}", css)
        styles = set(re.findall(r'style = "([A-Za-z]+)"', lua))
        known = set(reference_docx._STYLES)
        self.assertEqual(styles - known, set(), "DOCX styles missing for gold boxes")


class JustifyTests(unittest.TestCase):
    def test_pdf_html_docx_justify_body_text(self):
        template = (ASSETS / "typst-show.typ").read_text(encoding="utf-8")
        self.assertRegex(template, r"#set par\([^)]*justify: true")
        self.assertIn("hyphenate: true", template)
        for exempt in ("heading", "list", "enum", "table", "figure.caption"):
            self.assertIn(f"#show {exempt}: set par(justify: false)", template)
        css = (ASSETS / "textbook.css").read_text(encoding="utf-8")
        self.assertIn("text-align: justify", css)
        self.assertIn("hyphens: auto", css)
        styles = reference_docx._patch_styles(
            '<w:styles><w:style w:type="paragraph" w:styleId="BodyText"></w:style></w:styles>')
        body = re.search(r'w:styleId="BodyText">.*?</w:style>', styles, re.S).group(0)
        self.assertIn('<w:jc w:val="both"/>', body)
        settings = reference_docx._patch_settings(
            "<w:settings><w:zoom/><w:proofState/><w:defaultTabStop w:val=\"720\"/><w:characterSpacingControl/></w:settings>")
        self.assertIn('<w:defaultTabStop w:val="720"/><w:autoHyphenation w:val="true"/>', settings)
        self.assertLess(settings.index("<w:mirrorMargins/>"), settings.index("<w:proofState/>"))


class SlimHtmlTests(unittest.TestCase):
    def test_slim_html_drops_neighbour_pages_and_inline_theme_fonts(self):
        from urllib.parse import quote

        css = "@font-face{font-family:X;src:url(data:font/woff2;base64,AAAA)}body{color:red}"
        page = ("<html><head><title>t</title>"
                f'<link href="data:text/css,{quote(css)}" rel="stylesheet" id="quarto-bootstrap">'
                f'<link href="data:text/html,{quote("<html>" + "x" * 5000 + "</html>")}" rel="prev">'
                '</head><body><p>Hi</p></body></html>')
        slim = slim_html(page, "cdn")
        self.assertNotIn("data:text/html", slim)
        self.assertIn('<style id="quarto-bootstrap">body{color:red}</style>', slim)
        self.assertIn(GOOGLE_FONTS_CSS.replace("&", "&amp;"), slim)
        self.assertLess(len(slim), len(page) / 4)
        embedded = slim_html(page, "embed")
        self.assertIn("@font-face", embedded)
        self.assertNotIn("fonts.googleapis", embedded)


@unittest.skipUnless(os.environ.get("QUARTO_PATH") and os.environ.get("PHYSICS_FULL_RENDER"), "set PHYSICS_FULL_RENDER=1 for the full render")
class FullRenderTests(unittest.TestCase):
    def test_tricky_sample_in_all_formats(self):
        from physics_studio.render import render_formats
        from physics_studio.staging import stage_zip

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("_quarto.yml", "lang: en\n")
            archive.writestr("bab-01.qmd", TRICKY + "\n" + ExtrasTests.FRAME + "\n" + ExtrasTests.GRAPH)
        with tempfile.TemporaryDirectory() as work:
            work = Path(work)
            stage_zip(buffer.getvalue(), work)
            produced = render_formats(work, ["PDF", "DOCX", "HTML", "EPUB"], 600)
            out = work / "_output"
            pdf = subprocess.run(["pdftotext", str(out / produced["PDF"]), "-"], capture_output=True, text=True).stdout
            for leak in LEAKS:
                self.assertIsNone(re.search(leak, pdf), leak)
            self.assertIn("9.81 m/s", pdf)
            html = (out / produced["HTML"]).read_text(encoding="utf-8")
            self.assertLess(len(html), 3_000_000)
            self.assertNotIn("data:text/html", html)
            self.assertIn("<svg", html)
