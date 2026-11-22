#import "@preview/orange-book:0.7.1": book, part, chapter, appendices

#show: book.with(
  title: [$title$],
$if(subtitle)$
  subtitle: [$subtitle$],
$endif$
  author: "$for(by-author)$$it.name.literal$$sep$, $endfor$",
$if(date)$
  date: "$date$",
$endif$
  paper-size: "iso-b5",
  margin: (inside: 20mm, outside: 14mm, top: 18mm, bottom: 18mm),
  main-color: rgb("#0F2942"),
  font-size: 10.2pt,
  outline-depth: 3,
  lang: "$lang$",
)

#set text(font: ("Source Serif 4", "Libertinus Serif"), size: 10.2pt)
#show heading: set text(font: ("Inter", "Source Serif 4"))
#set par(leading: 0.48em)
