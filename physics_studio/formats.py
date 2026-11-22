"""Output formats shared by the worker and the generator."""

from __future__ import annotations

FORMATS = ("PDF", "DOCX", "HTML", "EPUB", "FLIPBOOK")

FILENAMES = {
    "PDF": "physics.pdf",
    "DOCX": "physics.docx",
    "HTML": "index.html",
    "EPUB": "physics.epub",
    "FLIPBOOK": "flipbook.html",
}

QUARTO_TARGETS = {
    "PDF": "typst",
    "DOCX": "docx",
    "HTML": "html",
    "EPUB": "epub",
}


def parse_format(name: str) -> list[str]:
    """Return the formats a job should produce.

    ``ALL`` renders every product from one upload. Any other accepted name
    renders just that product, which is the contract the Apps Script already uses.
    """
    key = (name or "").strip().upper()
    if key == "ALL":
        return list(FORMATS)
    if key not in FORMATS:
        raise KeyError(key)
    return [key]
