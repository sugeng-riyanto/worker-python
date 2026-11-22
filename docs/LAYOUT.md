# Layout spec: Bahasa Cerdas physics textbook (from the MCE and OUP references)

Sources studied (Drive folder "MCE" and "OUP", downloaded to `layout/ref/`):
- **MCE**: Marshall Cavendish Education, *Cambridge IGCSE Physics Student's Book*, ch. 2 "Motion", ch. 6 "Energy, Work and Power", plus cover/TOC. These are print PDFs with embedded fonts.
- **OUP**: Oxford University Press, *Cambridge International AS & A Level Physics*, ch. 1 "Kinematics", ch. 4 "Force and momentum", TOC, and "Key concepts". These are phone screenshots of an e-reader, so measurements are approximate. The 356 MB *Complete Physics 4th ed.* PDF was not downloaded.

Only layout and style are emulated. No publisher text, images, or logos were copied into the templates.

## 1. What the two references do

| Element | MCE (IGCSE Student's Book) | OUP (AS & A Level) |
| --- | --- | --- |
| Trim | ≈ 200 × 250 mm (from the crop marks; the PDF page is 213 × 273 mm including slug) | ≈ A4-ish portrait (aspect 0.79); screenshots, not measurable |
| Grid | 1 main column (~120 mm) plus a ~40 mm **outer sidebar**, mirrored verso/recto | 1 main column plus a ~55 mm **left sidebar** holding learning outcomes and figures |
| Body font | Myriad Pro Light/Regular ~10 pt, ragged right | Serif (Times/Minion-like) ~10 pt, ragged right |
| Heading font | Myriad Pro Bold Condensed / DIN Next Bold Condensed | Sans (Frutiger/Myriad-like) semibold |
| Palette | orange `#F47415` (tabs, banners, folios), peach `#FCD2A9`/`#FDE5D0`, table blue `#0089C0` with rows `#A8D8EB`/`#E1F2F8`, crimson worked examples, navy "Let's Practise", green/purple/pink sidebar notes | blue `#0282CB` (number block), light blue `#C4E0F5` band, definition boxes `#CCDFF0`, grey summary-test header, magenta key words |
| Chapter opener | full-bleed photo, white "CHAPTER" plus a huge number and title, orange intro panel with questions | white page, blue number block "1", blue rule, section "1.1" in a light-blue band |
| Section heading | orange rounded banner "2.1 Speed, Velocity and Acceleration" with a peach "In this section, you will learn the following:" panel attached underneath | number in a light-blue box, title in large blue sans, thin rule; learning outcomes in the sidebar |
| Sub-headings | "What is speed?" bold condensed ~18 pt, black | bold sans ~11 pt |
| Key terms | **bold dark blue** inline; definitions written as "**Speed** is …" | **bold magenta** inline; key statement in a full-width light-blue box, bold and centred |
| Worked example | white box, thin crimson rounded border, crimson tab "Worked Example 2D", "Solution" in bold | light-blue panel with a blue "Worked example" header bar, two columns |
| Practice | navy tab "Let's Practise 2.1", numbered questions with bold numbers | grey header "Summary test 1.6" with two columns of questions |
| Sidebar notes | Quick Check (with an icon), Enrichment Activity, Link, Helpful Notes, Let's Map It; small type with a coloured heading aligned right | Learning outcomes, figures with italic captions |
| Figures and tables | caption "**Figure 2.1** *italic text*" below the figure; table caption above, blue header row, banded rows, rounded corners | "**Figure 1** *italic*", tables plain |
| Running head | orange tab at the outer top corner, "Chapter 2" | small chapter name at the outer top, thin rule |
| Folio | orange block at the outer bottom corner with the page number, chapter title in orange next to it | page number at the outer bottom |
| End of chapter | "Let's Review" box (thin blue border, orange tab), "Section A: Multiple-choice Questions" / "Section B: Short-answer and Structured Questions" in orange bold, two columns, options A–D in a grid | "Exam-style and Practice Questions" on a peach band, two columns |

## 2. Proposed house style ("studio", default) plus an optional "classic" theme

The house style follows MCE: it is the friendlier student-book look and matches the existing Gold Standard boxes. From OUP it takes the full-width light-blue definition and equation boxes and a compact sidebar. Switching to `classic` (OUP-like: blue, serif body, numbered blue box headings) changes one setting (`bc-theme: classic`), so both themes ship.

| Token | studio | classic |
| --- | --- | --- |
| Trim | ISO B5 176 × 250 mm (unchanged: the series, QR slots, and page targets assume B5) | same |
| Margins | inner 17 mm; outer 49 mm = 6 mm gap + 34 mm sidebar + 9 mm; top 22 mm; bottom 24 mm; text block ≈ 110 mm (≈ 62 % of the width, like MCE) | same |
| Body | Source Sans 3 9.8 pt, leading ≈ 1.3, ragged right, paragraph space 0.95 em (free Myriad substitute) | Source Serif 4 9.6 pt |
| Headings | Barlow Condensed Bold/ExtraBold (free condensed substitute for Myriad Bold Cond/DIN Cond) | Source Sans 3 semibold |
| Primary | `#F47415` | `#0282CB` |
| Soft | `#FDE3CC` (objectives) | `#C4E0F5` |
| Table header / rows | `#0089C0` / `#E1F1FA`, `#F1F8FC` | `#0282CB` / `#CCDFF0` |
| Worked example | `#D5164F` | `#0282CB` |
| Practice | navy `#1B4F8A` | navy `#1D3F66` |
| Key terms | bold `#1B4F8A` | bold magenta `#B0287A` |
| Notes | green `#3E9B46`, purple `#7A4FA0`, red `#D62828`, grey `#6B7280` | same family |

### Heading hierarchy (PDF)
- **H1 chapter**: new page; orange panel spanning the main column and the sidebar, rounded bottom-right corner, faint decorative circles, "BAB" plus a 64 pt number plus a 25 pt title. Unnumbered chapters (Prakata, Front Matter) get the panel without a number.
- **H2 section**: numbered "2.1"; a 17 pt white-on-orange banner with rounded corners and a square bottom-left corner so the objectives panel attaches underneath. Unnumbered H2 (for example "Ayo Mengulang") uses a navy banner. classic: blue number box plus blue title plus rule.
- **H3**: 14.5 pt Barlow Condensed Bold, black (MCE "What is speed?").
- **H4**: 11.5 pt, orange. **H5**: bold body size, navy.

### Boxes (fenced divs → `bc-box` / `bc-aside`)
| Class | Look | Label (id / en) |
| --- | --- | --- |
| objectives | peach panel attached to the section banner | Dalam subbab ini, kamu akan mempelajari: |
| worked-example, givens | white, 1 pt crimson rounded border, crimson tab with auto number "Contoh Soal 2.1" | Contoh Soal / Worked Example |
| practice | navy border and tab, numbered | Ayo Berlatih / Let's Practise |
| review | spans the main column and the sidebar, blue border, orange tab | Ayo Mengulang / Let's Review |
| summary | light-blue fill, blue tab | Ringkasan |
| definition, key-equation | full-width light-blue, centred semibold (OUP) | — |
| workspace, think | green tint with a left rule | Ruang Kerja Aktif, Pertanyaan Pemantik |
| exam-trap | red tint with a left rule | Jebakan Ujian |
| hook | blue tint, orange rule (chapter opener) | Fenomena |
| practical | purple tint | Kegiatan Praktikum |
| figure-brief | dashed grey frame (diagram placeholder) | Ilustrasi |
| quick-check, remember, key-terms, qr, teacher-note, enrichment, info, link | **sidebar** note: coloured top rule, tinted fill, upper-case label aligned right (MCE); falls back to the main column above ~420 characters | Cek Cepat, Ingat!, Istilah Kunci, Pindai (with a dashed 18 mm QR slot), Catatan Guru, Pengayaan, Tahukah Kamu?, Tautan |

Short boxes never break across pages, so a tab is never orphaned. Boxes taller than 120 mm break normally.

### Figures, tables, lists
- Figure caption below: "**Gambar 1.1**" bold navy plus italic text, 8.6 pt, left aligned. Table caption above. Numbering is per chapter (`crossref.chapters`).
- Tables: blue header row with white bold text, banded rows, white hairlines, 2 mm rounded corners, 8.8 pt.
- Bullets: orange "•"; numbered lists use bold navy numbers.

### Running heads and folios
- Outer top corner: orange tab "Bab 2", hidden on chapter-opening pages and in unnumbered chapters.
- Outer bottom corner: orange folio block (page number in white) bleeding to the trim edge, with the chapter title in orange beside it.
- classic: grey "Bab 2 · Title" at the outer top with a light rule.

### Cover and contents
Solid primary cover with large decorative circles, "BUKU SISWA", the title in 36 pt condensed type, the subtitle, and the author. Then a blank page, then "Daftar Isi" with chapters in orange condensed bold.

### HTML / EPUB / flipbook / DOCX
- HTML/EPUB use `textbook.css`, the same tokens: chapter title band, section banners, tables, boxes, and sidebar notes floated right on desktop and stacked on phones. The HTML embeds Source Sans 3 and Barlow Condensed (WOFF2/TTF) so it looks the same without installed fonts.
- The flipbook is made from the PDF pages, so it inherits the PDF look.
- DOCX: Word has no font fallback, so it uses Calibri (body) and Arial Narrow (headings), which ship with Office. It has orange shaded H1/H2 bands, banded blue tables, and one paragraph style per box (BoxWorkedExample, BoxPractice, …). There is no sidebar in Word; notes become boxes.

## 3. Gaps that need content (generator), not templates
- Real photos and diagrams: the references depend on them. The generator only writes `[DIAGRAM BRIEF …]` placeholders, now drawn as dashed "Ilustrasi" frames.
- Options A–D in a two-column grid and two-column question layouts in "Let's Review" need a list convention (see `generator_prompt_changes.md`).
- Icons (Quick Check gauge, Link badge) are not reproduced; labels are text only.

## Authoring markup

```text
OUTPUT FORMAT (Quarto Markdown, renders as an MCE-style student book):
- Start with exactly one "# <Chapter title>" line. No "CHAPTER n:", "BAB n", or "Module n:" prefixes; numbering is automatic. Use Title Case, not ALL CAPS.
- Sections: "## <Section title>" (auto-numbered 2.1, 2.2 …). Sub-topics: "### <Question-style title>", e.g. "### Apa itu kelajuan?". Never output module or scaffold headings such as "Sub-Section Pedagogical Header" or "Module 6: G.I.V.E.N.S.".
- Front matter, Prakata, or an introduction that is not a chapter: "# Prakata {.unnumbered}".
- Math only as $...$ (inline) and $$...$$ (display). Never in backticks or code blocks. Units: $v = 12\ \text{m/s}$.
- Key terms: **bold** at first use. Define them as "**Kelajuan** adalah ...". A definition worth memorising goes in ::: {.definition}.
- Boxes are fenced divs. Never use blockquotes (">") or emoji-labelled lines as boxes:
  ::: {.objectives}            bullet list right after every ## heading
  ::: {.worked-example title="Menghitung kelajuan rata-rata"}
  Soal ...
  **G (Given):** ... **I:** ... **V:** ... **E:** ... **N:** ... **S:** ...
  **Penyelesaian**
  ...
  :::
  ::: {.practice}              2–4 numbered questions after each worked example
  ::: {.key-equation}          one display equation plus a one-line meaning
  ::: {.quick-check}           1–2 short questions (printed in the side column; keep under 60 words)
  ::: {.remember} / ::: {.key-terms} / ::: {.info} / ::: {.link}   short side notes (under 60 words)
  ::: {.qr title="PhET: ..."}  the URL plus one sentence (side column)
  ::: {.teacher-note}          duration, model, command verbs, verification stamp, rubric
  ::: {.figure-brief}          one diagram brief: what to draw, labels, vector colours
  ::: {.exam-trap}             a misconception and its correction (a 2-column table is fine)
  ::: {.workspace}             Predict / Observe / Explain lines "________"
  ::: {.hook} / ::: {.think} / ::: {.practical title="..."} / ::: {.summary}
- Tables: a pipe table plus a caption line ": Tabel caption {#tbl-xxx}" directly below.
  Figures: ![Caption](images/file.png){#fig-xxx}. Refer to them with @fig-xxx / @tbl-xxx.
- End of chapter: "## Ayo Mengulang {.unnumbered}" then ::: {.review} containing
  "#### Bagian A: Pilihan Ganda" (numbered questions; options as a nested list "A. ...", "B. ...")
  and "#### Bagian B: Uraian".
- Use plain text, not inline code, for emphasis.
```


## Palettes and depth (v14.1)

- Nine palettes, all WCAG AA (see README "Colour palettes"): studio, blue, classic, teal, forest, crimson, purple, amber, dark.
- The studio orange is slightly deeper (`#E5670C`) than MCE `#F47415`. White text on it reaches 3.35:1, which is enough for large text. Small orange text uses `primary-text` `#A84C08` (5.67:1).
- Depth:
  - PDF: 8 pt rounded corners on boxes, tables, and images; two offset shadow layers under the opener, section bands, and short boxes; gradient bands; an embossed chapter number and title (an offset darker copy plus a faint highlight); a gradient accent bar on H3; a translucent number chip in H2.
  - HTML: `box-shadow`, gradients, and an embossed `text-shadow`; no shadows in print.
