"""Plain text from a Google Docs API document resource."""

from __future__ import annotations


def document_plain_text(document: dict) -> str:
    chunks: list[str] = []

    def walk(elements: list) -> None:
        for element in elements or []:
            paragraph = element.get("paragraph")
            if paragraph:
                for item in paragraph.get("elements") or []:
                    run = item.get("textRun") or {}
                    if isinstance(run.get("content"), str):
                        chunks.append(run["content"])
            table = element.get("table")
            if table:
                for row in table.get("tableRows") or []:
                    for cell in row.get("tableCells") or []:
                        walk(cell.get("content") or [])
            toc = element.get("tableOfContents")
            if toc:
                walk(toc.get("content") or [])

    walk((document.get("body") or {}).get("content") or [])
    return "".join(chunks)
