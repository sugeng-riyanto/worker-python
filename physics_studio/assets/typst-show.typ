// Bahasa Cerdas textbook template (Quarto typst-show partial).
// Layout emulates modern IGCSE student books: B5 page, outer sidebar column,
// chapter tabs, banded section headings, and coloured learning boxes.
// Pandoc template: a literal dollar sign must be written twice.
#import "@preview/marginalia:0.3.1" as marginalia

#let bc-theme-name = "$if(bc-theme)$$bc-theme$$else$studio$endif$"
#let bc-lang = "$if(lang)$$lang$$else$en$endif$"
#let bc-id = bc-lang.starts-with("id")

// Themes set type and heading style; palettes set colour (see palettes.py,
// where every text/background pair is contrast-checked against WCAG AA).
#let bc-themes = (
  studio: (
    body-font: ("Source Sans 3", "Source Sans Pro", "Inter", "Libertinus Serif"),
    // Barlow Condensed registers as family "Barlow" with a condensed stretch.
    head-font: ("Barlow", "Source Sans 3", "Inter"),
    head-stretch: 75%,
    body-size: 9.8pt,
    banner: "band",
  ),
  classic: (
    body-font: ("Source Serif 4", "Source Serif Pro", "Libertinus Serif"),
    head-font: ("Source Sans 3", "Source Sans Pro", "Inter"),
    head-stretch: 100%,
    body-size: 9.6pt,
    banner: "number-box",
  ),
)
// <bc-palette> (replaced at staging time with the selected palette)
#let bc-palette-name = "studio"
#let bc-palette = (
  "paper": rgb("#FFFFFF"),
  "ink": rgb("#1F2328"),
  "heading": rgb("#1F2328"),
  "muted": rgb("#5B6270"),
  "surface": rgb("#FFFFFF"),
  "primary": rgb("#E5670C"),
  "primary-text": rgb("#A84C08"),
  "primary-soft": rgb("#FDE6D2"),
  "on-primary": rgb("#FFFFFF"),
  "accent": rgb("#C8144A"),
  "navy": rgb("#1B4F8A"),
  "blue": rgb("#0072A3"),
  "table-head": rgb("#006F9E"),
  "blue-soft": rgb("#E1F1FA"),
  "blue-softer": rgb("#F1F8FC"),
  "green": rgb("#2E7533"),
  "green-soft": rgb("#E5F3E3"),
  "purple": rgb("#6E4594"),
  "purple-soft": rgb("#EFE6F6"),
  "red": rgb("#B91F1F"),
  "red-soft": rgb("#FCE7E6"),
  "grey": rgb("#5F6672"),
  "grey-soft": rgb("#F1F2F4"),
)
#let bc-dark = false
// </bc-palette>
#let T = bc-themes.at(bc-theme-name, default: bc-themes.studio) + bc-palette
// Depth: soft layered shadow under boxes and bands; deeper band end for gradients.
#let bc-shadow = if bc-dark { black.transparentize(45%) } else { T.ink.transparentize(80%) }
#let bc-shadow-soft = if bc-dark { black.transparentize(70%) } else { T.ink.transparentize(90%) }
#let bc-deep(c) = if bc-dark { c.lighten(14%) } else { c.darken(16%) }
#let bc-band(c) = gradient.linear(c, bc-deep(c), angle: 20deg)
#let bc-radius = 8pt
#let bc-deco = if bc-dark { white.transparentize(86%) } else { black.transparentize(91%) }
// Draw `body` (a block) over two offset, rounded shadow layers. Unbreakable.
#let bc-lift(body, radius: bc-radius, dx: 1.1mm, dy: 1.3mm) = layout(size => {
  let m = measure(width: size.width, body)
  block(breakable: false, above: 1.4em, below: 1.3em, {
    place(top + left, dx: dx, dy: dy, rect(width: m.width, height: m.height, radius: radius, fill: bc-shadow-soft))
    place(top + left, dx: dx * 0.5, dy: dy * 0.55, rect(width: m.width, height: m.height, radius: radius, fill: bc-shadow))
    body
  })
})
// Embossed text: a darker offset copy below and a faint highlight above.
#let bc-emboss(fill: T.on-primary, depth: 1.6pt, body) = box({
  place(dx: depth, dy: depth, text(fill: bc-deep(bc-deep(T.primary)).transparentize(20%), body))
  place(dx: -depth * 0.35, dy: -depth * 0.35, text(fill: white.transparentize(if bc-dark { 80% } else { 72% }), body))
  text(fill: fill, body)
})

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
#set page(paper: "iso-b5", fill: T.paper)
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
#show strong: set text(fill: T.navy)
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
      box(width: 26mm, height: 9mm, fill: bc-band(T.primary), radius: if odd { (top-left: 3mm) } else { (top-right: 3mm) },
        align(if odd { left + horizon } else { right + horizon },
          pad(x: 5mm, text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: 14pt, fill: T.on-primary)[#p]))))
    if h != none {
      let title = h.body
      place(bottom + side, dx: if odd { -30mm } else { 30mm }, dy: -11.6mm,
        box(width: 100mm, align(side, text(font: T.head-font, stretch: T.head-stretch, weight: "semibold", size: 10pt, fill: T.primary-text)[#title])))
    }
    let tag = bc-chapter-tag(h)
    if tag != none and not starts {
      if T.banner == "band" {
        place(top + side, dy: 6mm,
          box(width: 34mm, height: 11mm, fill: bc-band(T.primary), radius: if odd { (top-left: 4mm, bottom-left: 4mm) } else { (top-right: 4mm, bottom-right: 4mm) },
            align(center + horizon, text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: 14pt, fill: T.on-primary)[#tag])))
      } else {
        place(top + side, dx: if odd { -bc-outer-far } else { bc-outer-far }, dy: 10mm,
          text(font: T.head-font, stretch: T.head-stretch, size: 8.5pt, fill: T.muted)[#tag · #h.body])
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
    #bc-lift(radius: 10mm, dx: 1.6mm, dy: 2mm, block(width: 100%, fill: bc-band(T.primary), radius: (bottom-right: 10mm, top-left: 3mm, top-right: 3mm, bottom-left: 3mm), inset: (x: 8mm, top: 8mm, bottom: 9mm), below: 0mm, clip: true)[
      #place(top + right, dx: 8mm, dy: -7mm, box(width: 52mm, height: 62mm, clip: true,
        place(top + left, dx: 8mm, dy: 0mm, circle(radius: 34mm, fill: bc-deco))))
      #place(bottom + right, dx: 2mm, dy: 4mm, circle(radius: 16mm, fill: bc-deco))
      #if numbered {
        text(font: T.head-font, stretch: T.head-stretch, weight: "semibold", size: 15pt, fill: T.on-primary, tracking: 0.08em)[#upper(bc-label("Bab", "Chapter"))]
        v(-6pt)
        text(font: T.head-font, stretch: T.head-stretch, weight: "extrabold", size: 64pt, bc-emboss(fill: T.on-primary, depth: 2.4pt)[#n])
        v(-14pt)
      } else {
        v(18mm)
      }
      #block(width: 88%, text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: 25pt, hyphenate: false, bc-emboss(fill: T.on-primary, depth: 1.1pt)[#it.body]))
    ])
    #v(4mm)
  ]
}

#show heading.where(level: 2): it => {
  let numbered = it.numbering != none
  let num = if numbered { counter(heading).display() } else { none }
  if T.banner == "band" {
    let c = if numbered { T.primary } else { T.navy }
    let r = (top-left: bc-radius, top-right: bc-radius, bottom-right: bc-radius, bottom-left: if numbered { 0mm } else { bc-radius })
    let band = block(width: 100%, fill: bc-band(c), radius: r, inset: (x: 4mm, y: 2.6mm),
      text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: 17pt, fill: T.on-primary, hyphenate: false)[#if numbered [#box(fill: T.on-primary.transparentize(82%), radius: 4pt, inset: (x: 2.2mm, y: 0.6mm), outset: (y: 0.6mm))[#num]#h(0.5em)]#it.body])
    block(above: 1.6em, below: 0.9em, sticky: true, breakable: false, layout(size => {
      let m = measure(width: size.width, band)
      place(top + left, dx: 0.9mm, dy: 1.1mm, rect(width: m.width, height: m.height, radius: r, fill: bc-shadow))
      band
    }))
  } else {
    block(width: 100%, above: 1.8em, below: 1em, sticky: true, stroke: (bottom: 0.8pt + T.primary),
      grid(columns: (auto, 1fr), column-gutter: 4mm,
        box(fill: bc-band(T.primary), radius: 5pt, inset: (x: 3mm, y: 2.4mm), text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: 15pt, fill: T.on-primary)[#if numbered [#num] else [▸]]),
        align(horizon, text(font: T.head-font, stretch: T.head-stretch, weight: "semibold", size: 16pt, fill: T.primary-text, hyphenate: false)[#it.body])))
  }
}

#show heading.where(level: 3): it => block(above: 1.4em, below: 0.7em, sticky: true,
  grid(columns: (3.2pt, 1fr), column-gutter: 5pt,
    block(width: 3.2pt, height: if T.banner == "band" { 13pt } else { 11pt }, radius: 1.6pt, fill: bc-band(T.primary), above: 0pt),
    text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: if T.banner == "band" { 14.5pt } else { 12pt }, fill: if T.banner == "band" { T.heading } else { T.navy }, hyphenate: false)[#it.body]))

#show heading.where(level: 4): it => block(above: 1.2em, below: 0.6em, sticky: true,
  text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: 11.5pt, fill: T.primary-text, hyphenate: false)[#it.body])

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
  stroke: (x, y) => (bottom: 0.5pt + T.paper, right: 0.5pt + T.paper),
  fill: (x, y) => if y == 0 { T.table-head } else if calc.odd(y) { T.blue-soft } else { T.blue-softer },
  inset: (x: 6pt, y: 4.5pt),
)
#show table.cell.where(y: 0): set text(fill: T.on-primary, weight: "bold")
#show table.cell.where(y: 0): set strong(delta: 0)
#show table: set text(size: 8.8pt)
#show table: it => block(radius: bc-radius, clip: true, stroke: 0.6pt + T.blue-soft, it)
#show image: it => box(radius: 6pt, clip: true, it)

#show raw.where(block: false): it => text(font: T.head-font, stretch: T.head-stretch, weight: "semibold", fill: T.navy, it.text)
#show raw.where(block: true): it => block(width: 100%, fill: T.grey-soft, inset: 6pt, radius: 6pt, text(size: 8.5pt, it))
#show quote.where(block: true): it => block(width: 100%, fill: T.blue-softer, stroke: (left: 2pt + T.blue), inset: (x: 8pt, y: 6pt), radius: (right: 6pt), it.body)

// ---------- learning boxes (used by gold-boxes.lua) ----------
#let bc-box-styles = (
  objectives: (fill: T.primary-soft, stroke: none, head: T.ink, tab: none),
  "worked-example": (fill: T.surface, stroke: 1pt + T.accent, head: T.on-primary, tab: T.accent),
  givens: (fill: T.surface, stroke: 1pt + T.accent, head: T.on-primary, tab: T.accent),
  practice: (fill: T.surface, stroke: 1pt + T.navy, head: T.on-primary, tab: T.navy),
  review: (fill: T.surface, stroke: 1pt + T.blue, head: T.on-primary, tab: T.primary),
  summary: (fill: T.blue-softer, stroke: 0.8pt + T.blue, head: T.on-primary, tab: T.blue),
  definition: (fill: T.blue-soft, stroke: none, head: T.navy, tab: none),
  "key-equation": (fill: T.blue-soft, stroke: none, head: T.navy, tab: none),
  workspace: (fill: T.green-soft, stroke: (left: 3pt + T.green), head: T.green, tab: none),
  "exam-trap": (fill: T.red-soft, stroke: (left: 3pt + T.red), head: T.red, tab: none),
  hook: (fill: T.blue-softer, stroke: (left: 3pt + T.primary), head: T.primary-text, tab: none),
  practical: (fill: T.purple-soft, stroke: (left: 3pt + T.purple), head: T.purple, tab: none),
  note: (fill: T.grey-soft, stroke: (left: 3pt + T.grey), head: T.grey, tab: none),
  "figure-brief": (fill: T.surface, stroke: (paint: T.grey, thickness: 0.8pt, dash: "dashed"), head: T.grey, tab: none),
)

#let bc-box(kind: "note", title: none, wide: false, body) = {
  let s = bc-box-styles.at(kind, default: bc-box-styles.note)
  let content = if s.tab != none { layout(size => {
    // Keep short boxes whole so the coloured tab never sits alone at a page foot.
    let tall = measure(block(width: size.width - 8mm, body)).height > 120mm
    let b = block(width: 100%, stroke: s.stroke, fill: s.fill, radius: bc-radius, inset: (x: 4mm, top: 0mm, bottom: 3.5mm), above: 1.4em, below: 1.2em, breakable: tall)[
      #if title != none {
        move(dx: -4mm, block(fill: bc-band(s.tab), inset: (x: 4mm, y: 2.2mm), radius: (top-left: bc-radius, bottom-right: bc-radius), below: 0.9em, sticky: true,
          text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: 14pt, fill: s.head)[#title]))
      } else { v(3mm) }
      #body
    ]
    if tall { b } else { bc-lift(b) }
  }) } else if kind == "objectives" {
    block(width: 100%, fill: s.fill, radius: (bottom-left: bc-radius, bottom-right: bc-radius, top-right: bc-radius), inset: (x: 4mm, y: 3mm), above: -0.5em, below: 1.3em, breakable: false)[
      #if title != none { text(weight: "bold", size: 10.2pt, fill: T.ink)[#title]; v(0.2em) }
      #body
    ]
  } else if kind == "definition" or kind == "key-equation" {
    bc-lift(dx: 0.8mm, dy: 1mm, block(width: 100%, fill: s.fill, radius: bc-radius, stroke: 0.6pt + T.navy.transparentize(70%), inset: (x: 5mm, y: 3mm), breakable: false)[
      #set align(center)
      #set text(weight: "semibold")
      #if title != none { text(font: T.head-font, stretch: T.head-stretch, weight: "bold", fill: s.head, size: 10pt)[#upper(title)]; parbreak() }
      #body
    ])
  } else {
    block(width: 100%, fill: s.fill, stroke: s.stroke, radius: bc-radius, inset: (x: 4mm, y: 3mm), above: 1.2em, below: 1.2em, breakable: true)[
      #if title != none { text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: 11pt, fill: s.head)[#title]; v(0.15em) }
      #body
    ]
  }
  if wide { marginalia.wideblock(side: "outer", content) } else { content }
}

// Sidebar notes (Quick check, Remember, Key terms, QR, Teacher note, Enrichment).
#let bc-aside-styles = (
  "quick-check": (color: T.green, fill: T.green-soft),
  remember: (color: T.primary-text, fill: T.primary-soft),
  "key-terms": (color: T.navy, fill: T.blue-soft),
  qr: (color: T.navy, fill: T.surface),
  "teacher-note": (color: T.grey, fill: T.grey-soft),
  enrichment: (color: T.purple, fill: T.purple-soft),
  info: (color: T.blue, fill: T.blue-softer),
  link: (color: T.accent, fill: T.red-soft),
)
#let bc-aside(kind: "info", title: none, body) = {
  let s = bc-aside-styles.at(kind, default: bc-aside-styles.info)
  marginalia.note(counter: none, shift: "avoid", text-style: (size: 8.2pt), par-style: (spacing: 0.7em, leading: 0.5em),
    block(width: 100%, fill: s.fill, stroke: (top: 2pt + s.color), inset: (x: 2.2mm, y: 2.2mm), radius: (bottom-left: 6pt, bottom-right: 6pt, top-right: 2pt, top-left: 2pt))[
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
  #block(width: 100%, height: 100%, fill: bc-band(T.primary))[
    #place(top + right, dx: 40mm, dy: -30mm, circle(radius: 70mm, fill: bc-deco))
    #place(bottom + left, dx: -25mm, dy: 25mm, circle(radius: 55mm, fill: bc-deco))
    #pad(x: 18mm, top: 60mm)[
      // Only large type (>= 14 pt bold / 18 pt) sits directly on the band.
      #text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: 14pt, fill: T.on-primary, tracking: 0.12em)[#upper(bc-label("Buku Siswa", "Student's Book"))]
      #v(4mm)
      #text(font: T.head-font, stretch: T.head-stretch, weight: "extrabold", size: 36pt, hyphenate: false, bc-emboss(fill: T.on-primary, depth: 1.6pt)[$title$])
$if(subtitle)$
      #v(2mm)
      #text(font: T.head-font, stretch: T.head-stretch, weight: "semibold", size: 18pt, fill: T.on-primary)[$subtitle$]
$endif$
      #v(1fr)
    ]
    // Small type goes on a solid navy plate so it keeps 4.5:1 in every palette.
    #place(bottom + left, dx: 18mm, dy: -18mm, block(width: 120mm, fill: T.navy, radius: bc-radius, inset: (x: 5mm, y: 3.5mm))[
      #text(size: 11pt, fill: T.on-primary, weight: "semibold")[$for(by-author)$$it.name.literal$$sep$, $endfor$]
$if(date)$
      #linebreak()#text(size: 9pt, fill: T.on-primary)[$date$]
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
    text(font: T.head-font, stretch: T.head-stretch, weight: "bold", size: 12pt, fill: T.primary-text, it)
  }
  #show outline.entry.where(level: 2): it => text(size: 9.5pt, it)
  #outline(title: none, depth: 2, indent: 1.2em)
]
