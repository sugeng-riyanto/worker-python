// Bahasa Cerdas textbook template (Quarto typst-show partial).
// Layout emulates modern IGCSE student books: B5 page, outer sidebar column,
// chapter tabs, banded section headings, and coloured learning boxes.
// Pandoc template: a literal dollar sign must be written twice.
#import "@preview/marginalia:0.3.1" as marginalia

#let bc-theme-name = "$if(bc-theme)$$bc-theme$$else$studio$endif$"
#let bc-lang = "$if(lang)$$lang$$else$en$endif$"
#let bc-id = bc-lang.starts-with("id")

#let bc-themes = (
  studio: (
    primary: rgb("#F47415"),
    primary-dark: rgb("#C85F05"),
    primary-soft: rgb("#FDE3CC"),
    accent: rgb("#D5164F"),
    navy: rgb("#1B4F8A"),
    term: rgb("#1B4F8A"),
    blue: rgb("#0089C0"),
    blue-soft: rgb("#E1F1FA"),
    blue-softer: rgb("#F1F8FC"),
    green: rgb("#3E9B46"),
    green-soft: rgb("#E5F3E3"),
    purple: rgb("#7A4FA0"),
    purple-soft: rgb("#EFE6F6"),
    red: rgb("#D62828"),
    red-soft: rgb("#FCE7E6"),
    grey: rgb("#6B7280"),
    grey-soft: rgb("#F2F2F2"),
    ink: rgb("#1F2328"),
    body-font: ("Source Sans 3", "Source Sans Pro", "Inter", "Libertinus Serif"),
    // Barlow Condensed registers as family "Barlow" with a condensed stretch.
    head-font: ("Barlow", "Source Sans 3", "Inter"),
    head-stretch: 75%,
    body-size: 9.8pt,
    banner: "band",
  ),
  classic: (
    primary: rgb("#0282CB"),
    primary-dark: rgb("#1D5D97"),
    primary-soft: rgb("#C4E0F5"),
    accent: rgb("#0282CB"),
    navy: rgb("#1D3F66"),
    term: rgb("#B0287A"),
    blue: rgb("#0282CB"),
    blue-soft: rgb("#CCDFF0"),
    blue-softer: rgb("#EEF5FB"),
    green: rgb("#3E8E5E"),
    green-soft: rgb("#E4F1E8"),
    purple: rgb("#6D4C9A"),
    purple-soft: rgb("#ECE5F5"),
    red: rgb("#C0392B"),
    red-soft: rgb("#FBE9E7"),
    grey: rgb("#8A8F98"),
    grey-soft: rgb("#EDEDED"),
    ink: rgb("#1A1A1A"),
    body-font: ("Source Serif 4", "Source Serif Pro", "Libertinus Serif"),
    head-font: ("Source Sans 3", "Source Sans Pro", "Inter"),
    head-stretch: 100%,
    body-size: 9.6pt,
    banner: "number-box",
  ),
)
#let T = bc-themes.at(bc-theme-name, default: bc-themes.studio)

#let bc-label(id, en) = if bc-id { id } else { en }

// Page geometry: ISO B5 (176 × 250 mm). Inner margin 17 mm; outer margin
// holds a 34 mm sidebar for notes, figures, and quick checks.
#let bc-inner = 17mm
#let bc-side = 34mm
#let bc-side-sep = 6mm
#let bc-outer-far = 9mm
#let bc-outer = bc-outer-far + bc-side + bc-side-sep
#let bc-top = 22mm
#let bc-bottom = 24mm

#set document(title: [$title$], author: "$for(by-author)$$it.name.literal$$sep$, $endfor$")
#set page(paper: "iso-b5")
#show: marginalia.setup.with(
  inner: (far: bc-inner - 2mm, width: 1mm, sep: 1mm),
  outer: (far: bc-outer-far, width: bc-side, sep: bc-side-sep),
  top: bc-top,
  bottom: bc-bottom,
  book: true,
  clearance: 8pt,
)

#set text(font: T.body-font, size: T.body-size, fill: T.ink, lang: bc-lang.slice(0, 2), hyphenate: true)
#set par(leading: 0.62em, spacing: 0.95em, justify: false)
#show strong: set text(fill: T.term)
#show math.equation: set text(font: ("New Computer Modern Math",))
#set list(marker: (text(fill: T.primary, size: 1.15em, baseline: -0.05em)[•], text(fill: T.primary)[–]), indent: 0.2em, body-indent: 0.55em)
#set enum(numbering: n => text(weight: "bold", fill: T.navy)[#n], indent: 0.1em, body-indent: 0.6em)
#show link: set text(fill: T.blue)

// ---------- running heads and folios ----------
#let bc-chapter-on(page) = {
  let hs = query(heading.where(level: 1)).filter(h => h.location().page() <= page)
  if hs.len() == 0 { none } else { hs.last() }
}
#let bc-chapter-starts(page) = query(heading.where(level: 1)).any(h => h.location().page() == page)
#let bc-chapter-tag(h) = {
  if h == none or h.numbering == none { return none }
  let n = counter(heading).at(h.location()).first()
  [#bc-label("Bab", "Chapter") #n]
}

#set page(
  header: none,
  footer: none,
  background: context {
    let p = here().page()
    let odd = calc.odd(p)
    if p <= 2 { return }
    let h = bc-chapter-on(p)
    let starts = bc-chapter-starts(p)
    let side = if odd { right } else { left }
    // folio block bleeding off the outer bottom corner
    place(bottom + side, dy: -9mm,
      box(width: 26mm, height: 9mm, fill: T.primary,
        align(if odd { left + horizon } else { right + horizon },
          pad(x: 5mm, text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: 12pt, fill: white)[#p]))))
    if h != none {
      let title = h.body
      place(bottom + side, dx: if odd { -30mm } else { 30mm }, dy: -11.6mm,
        box(width: 100mm, align(side, text(font: T.head-font, stretch: T.head-stretch, weight: "semibold", size: 10pt, fill: T.primary)[#title])))
    }
    let tag = bc-chapter-tag(h)
    if tag != none and not starts {
      if T.banner == "band" {
        place(top + side, dy: 6mm,
          box(width: 34mm, height: 11mm, fill: T.primary, radius: if odd { (top-left: 4mm, bottom-left: 4mm) } else { (top-right: 4mm, bottom-right: 4mm) },
            align(center + horizon, text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: 12pt, fill: white)[#tag])))
      } else {
        place(top + side, dx: if odd { -bc-outer-far } else { bc-outer-far }, dy: 10mm,
          text(font: T.head-font, stretch: T.head-stretch, size: 8.5pt, fill: T.grey)[#tag · #h.body])
        place(top + left, dx: bc-inner - 2mm, dy: 14mm, line(length: 176mm - bc-inner - bc-outer-far + 2mm, stroke: 0.4pt + T.primary-soft))
      }
    }
  },
)

// ---------- headings ----------
#set heading(numbering: (..n) => {
  let parts = n.pos()
  if parts.len() == 1 { str(parts.at(0)) } else if parts.len() == 2 { str(parts.at(0)) + "." + str(parts.at(1)) } else { none }
})

#show heading.where(level: 1): it => {
  pagebreak(weak: true)
  counter("bc-example").update(0)
  counter("bc-practice").update(0)
  let numbered = it.numbering != none
  let n = if numbered { counter(heading).get().first() } else { none }
  marginalia.wideblock(side: "outer")[
    #block(width: 100%, fill: T.primary, radius: (bottom-right: 10mm), inset: (x: 8mm, top: 8mm, bottom: 9mm), below: 10mm, clip: true)[
      #place(top + right, dx: 8mm, dy: -7mm, box(width: 52mm, height: 62mm, clip: true,
        place(top + left, dx: 8mm, dy: 0mm, circle(radius: 34mm, fill: white.transparentize(88%)))))
      #place(bottom + right, dx: 2mm, dy: 4mm, circle(radius: 16mm, fill: white.transparentize(90%)))
      #if numbered {
        text(font: T.head-font, stretch: T.head-stretch, weight: "semibold", size: 15pt, fill: white, tracking: 0.08em)[#upper(bc-label("Bab", "Chapter"))]
        v(-6pt)
        text(font: T.head-font, stretch: T.head-stretch, weight: "extrabold", size: 64pt, fill: white)[#n]
        v(-14pt)
      } else {
        v(18mm)
      }
      #block(width: 88%, text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: 25pt, fill: white, hyphenate: false)[#it.body])
    ]
  ]
}

#show heading.where(level: 2): it => {
  let numbered = it.numbering != none
  let num = if numbered { counter(heading).display() } else { none }
  if T.banner == "band" {
    block(width: 100%, fill: if numbered { T.primary } else { T.navy }, radius: (top-left: 3mm, top-right: 3mm, bottom-right: 3mm, bottom-left: if numbered { 0mm } else { 3mm }),
      inset: (x: 4mm, y: 2.6mm), above: 1.6em, below: 0.9em, sticky: true,
      text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: 17pt, fill: white, hyphenate: false)[#if numbered [#num#h(0.45em)]#it.body])
  } else {
    block(width: 100%, above: 1.8em, below: 1em, sticky: true, stroke: (bottom: 0.8pt + T.primary),
      grid(columns: (auto, 1fr), column-gutter: 4mm,
        box(fill: T.primary, inset: (x: 3mm, y: 2.4mm), text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: 15pt, fill: white)[#if numbered [#num] else [▸]]),
        align(horizon, text(font: T.head-font, stretch: T.head-stretch, weight: "semibold", size: 16pt, fill: T.primary, hyphenate: false)[#it.body])))
  }
}

#show heading.where(level: 3): it => block(above: 1.4em, below: 0.7em, sticky: true,
  text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: if T.banner == "band" { 14.5pt } else { 12pt }, fill: if T.banner == "band" { T.ink } else { T.navy }, hyphenate: false)[#it.body])

#show heading.where(level: 4): it => block(above: 1.2em, below: 0.6em, sticky: true,
  text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: 11.5pt, fill: T.primary, hyphenate: false)[#it.body])

#show heading.where(level: 5): it => block(above: 1em, below: 0.5em, sticky: true,
  text(weight: "bold", size: T.body-size, fill: T.navy)[#it.body])

// ---------- figures and tables ----------
#show figure.caption: it => {
  set text(size: 8.6pt, style: "italic")
  set align(left)
  [#text(weight: "bold", fill: T.navy)[#it.supplement #context it.counter.display(it.numbering)]#h(0.4em)#it.body]
}
#show figure.where(kind: table): set figure.caption(position: top)
#show figure: set block(above: 1.2em, below: 1.2em)
#set table(
  stroke: (x, y) => (bottom: 0.5pt + white, right: 0.5pt + white),
  fill: (x, y) => if y == 0 { T.blue } else if calc.odd(y) { T.blue-soft } else { T.blue-softer },
  inset: (x: 6pt, y: 4.5pt),
)
#show table.cell.where(y: 0): set text(fill: white, weight: "bold")
#show table.cell.where(y: 0): set strong(delta: 0)
#show table: set text(size: 8.8pt)
#show table: it => block(radius: 2mm, clip: true, it)

#show raw.where(block: false): it => text(font: T.head-font, stretch: T.head-stretch, weight: "semibold", fill: T.navy, it.text)
#show raw.where(block: true): it => block(width: 100%, fill: T.grey-soft, inset: 6pt, radius: 2pt, text(size: 8.5pt, it))
#show quote.where(block: true): it => block(width: 100%, fill: T.blue-softer, stroke: (left: 2pt + T.blue), inset: (x: 8pt, y: 6pt), radius: (right: 2pt), it.body)

// ---------- learning boxes (used by gold-boxes.lua) ----------
#let bc-box-styles = (
  objectives: (fill: T.primary-soft, stroke: none, head: T.ink, tab: none),
  "worked-example": (fill: white, stroke: 1pt + T.accent, head: white, tab: T.accent),
  givens: (fill: white, stroke: 1pt + T.accent, head: white, tab: T.accent),
  practice: (fill: white, stroke: 1pt + T.navy, head: white, tab: T.navy),
  review: (fill: white, stroke: 1pt + T.blue, head: white, tab: T.primary),
  summary: (fill: T.blue-softer, stroke: 0.8pt + T.blue, head: white, tab: T.blue),
  definition: (fill: T.blue-soft, stroke: none, head: T.navy, tab: none),
  "key-equation": (fill: T.blue-soft, stroke: none, head: T.navy, tab: none),
  workspace: (fill: T.green-soft, stroke: (left: 3pt + T.green), head: T.green, tab: none),
  "exam-trap": (fill: T.red-soft, stroke: (left: 3pt + T.red), head: T.red, tab: none),
  hook: (fill: T.blue-softer, stroke: (left: 3pt + T.primary), head: T.primary-dark, tab: none),
  practical: (fill: T.purple-soft, stroke: (left: 3pt + T.purple), head: T.purple, tab: none),
  note: (fill: T.grey-soft, stroke: (left: 3pt + T.grey), head: T.grey, tab: none),
  "figure-brief": (fill: white, stroke: (paint: T.grey, thickness: 0.8pt, dash: "dashed"), head: T.grey, tab: none),
)

#let bc-box(kind: "note", title: none, wide: false, body) = {
  let s = bc-box-styles.at(kind, default: bc-box-styles.note)
  let content = if s.tab != none { layout(size => {
    // Keep short boxes whole so the coloured tab never sits alone at a page foot.
    let tall = measure(block(width: size.width - 8mm, body)).height > 120mm
    block(width: 100%, stroke: s.stroke, fill: s.fill, radius: 2.5mm, inset: (x: 4mm, top: 0mm, bottom: 3.5mm), above: 1.4em, below: 1.2em, breakable: tall)[
      #if title != none {
        move(dx: -4mm, block(fill: s.tab, inset: (x: 4mm, y: 2.2mm), radius: (top-left: 2.5mm, bottom-right: 3mm), below: 0.9em, sticky: true,
          text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: 13pt, fill: s.head)[#title]))
      } else { v(3mm) }
      #body
    ]
  }) } else if kind == "objectives" {
    block(width: 100%, fill: s.fill, radius: (bottom-left: 3mm, bottom-right: 3mm, top-right: 3mm), inset: (x: 4mm, y: 3mm), above: -0.5em, below: 1.3em, breakable: false)[
      #if title != none { text(weight: "bold", size: 10.2pt, fill: T.ink)[#title]; v(0.2em) }
      #body
    ]
  } else if kind == "definition" or kind == "key-equation" {
    block(width: 100%, fill: s.fill, inset: (x: 5mm, y: 3mm), above: 1em, below: 1em, breakable: false)[
      #set align(center)
      #set text(weight: "semibold")
      #if title != none { text(font: T.head-font, stretch: T.head-stretch, weight: "bold", fill: s.head, size: 10pt)[#upper(title)]; parbreak() }
      #body
    ]
  } else {
    block(width: 100%, fill: s.fill, stroke: s.stroke, radius: 2pt, inset: (x: 4mm, y: 3mm), above: 1.2em, below: 1.2em, breakable: true)[
      #if title != none { text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: 11pt, fill: s.head)[#title]; v(0.15em) }
      #body
    ]
  }
  if wide { marginalia.wideblock(side: "outer", content) } else { content }
}

// Sidebar notes (Quick check, Remember, Key terms, QR, Teacher note, Enrichment).
#let bc-aside-styles = (
  "quick-check": (color: T.green, fill: T.green-soft),
  remember: (color: T.primary, fill: T.primary-soft),
  "key-terms": (color: T.navy, fill: T.blue-soft),
  qr: (color: T.navy, fill: white),
  "teacher-note": (color: T.grey, fill: T.grey-soft),
  enrichment: (color: T.purple, fill: T.purple-soft),
  info: (color: T.blue, fill: T.blue-softer),
  link: (color: T.accent, fill: T.red-soft),
)
#let bc-aside(kind: "info", title: none, body) = {
  let s = bc-aside-styles.at(kind, default: bc-aside-styles.info)
  marginalia.note(counter: none, shift: "avoid", text-style: (size: 8.2pt), par-style: (spacing: 0.7em, leading: 0.5em),
    block(width: 100%, fill: s.fill, stroke: (top: 2pt + s.color), inset: (x: 2.2mm, y: 2.2mm), radius: (bottom-left: 2mm, bottom-right: 2mm))[
      #set list(marker: text(fill: s.color)[•], indent: 0pt, body-indent: 0.4em)
      #set enum(numbering: "1", indent: 0pt, body-indent: 0.4em)
      #if title != none { align(right, text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: 9.5pt, fill: s.color)[#upper(title)]); v(-0.3em) }
      #if kind == "qr" { align(center, box(width: 18mm, height: 18mm, stroke: (paint: s.color, thickness: 0.8pt, dash: "dashed"), align(center + horizon, text(size: 7pt, fill: s.color)[QR]))); v(0.2em) }
      #body
    ])
}

// Numbered boxes restart in every chapter: "Contoh Soal 2.3".
#let bc-number(kind) = {
  let c = counter("bc-" + kind)
  c.step()
  context {
    let ch = counter(heading).get().first()
    str(ch) + "." + str(c.get().first())
  }
}

#let bc-write-lines(n) = for _ in range(n) { v(5mm); line(length: 100%, stroke: 0.4pt + T.grey) }

// ---------- cover and contents ----------
#page(margin: 0pt, background: none)[
  #block(width: 100%, height: 100%, fill: T.primary)[
    #place(top + right, dx: 40mm, dy: -30mm, circle(radius: 70mm, fill: white.transparentize(88%)))
    #place(bottom + left, dx: -25mm, dy: 25mm, circle(radius: 55mm, fill: white.transparentize(90%)))
    #pad(x: 18mm, top: 60mm)[
      #text(font: T.head-font, stretch: T.head-stretch, weight: "semibold", size: 13pt, fill: white, tracking: 0.12em)[#upper(bc-label("Buku Siswa", "Student's Book"))]
      #v(4mm)
      #text(font: T.head-font, stretch: T.head-stretch, weight: "extrabold", size: 36pt, fill: white, hyphenate: false)[$title$]
$if(subtitle)$
      #v(2mm)
      #text(font: T.head-font, stretch: T.head-stretch, weight: "medium", size: 16pt, fill: white)[$subtitle$]
$endif$
      #v(1fr)
    ]
    #place(bottom + left, dx: 18mm, dy: -20mm, block(width: 140mm)[
      #line(length: 40mm, stroke: 2pt + white)
      #v(2mm)
      #text(size: 11pt, fill: white, weight: "semibold")[$for(by-author)$$it.name.literal$$sep$, $endfor$]
$if(date)$
      #linebreak()#text(size: 9pt, fill: white)[$date$]
$endif$
    ])
  ]
]
#page(background: none)[]
#page(background: none)[
  #set par(leading: 0.5em)
  #text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: 26pt, fill: T.primary)[#bc-label("Daftar Isi", "Contents")]
  #v(4mm)
  #show outline.entry.where(level: 1): it => {
    v(0.9em, weak: true)
    text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: 12pt, fill: T.primary, it)
  }
  #show outline.entry.where(level: 2): it => text(size: 9.5pt, it)
  #outline(title: none, depth: 2, indent: 1.2em)
]
