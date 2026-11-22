"""Read book metadata from an author ``_quarto.yml`` without trusting the rest of it."""

from __future__ import annotations

from dataclasses import dataclass, field

import yaml


class MetadataError(ValueError):
    """The supplied project file could not be used."""


@dataclass
class BookMetadata:
    title: str = "Physics Textbook Studio"
    subtitle: str = ""
    author: str = "Academic Physics Publishing Team"
    lang: str = "id"
    date: str = ""
    cover_image: str = ""
    description: str = ""
    publisher: str = ""
    rights: str = ""
    identifier: str = ""
    css_files: list[str] = field(default_factory=list)

    def as_yaml_document(self) -> dict:
        """Metadata fragment stored back into a generated archive."""
        book: dict = {"title": self.title, "author": self.author}
        if self.subtitle:
            book["subtitle"] = self.subtitle
        if self.cover_image:
            book["cover-image"] = self.cover_image
        document: dict = {"book": book, "lang": self.lang}
        epub: dict = {}
        if self.date:
            epub["date"] = self.date
        if self.cover_image:
            epub["cover-image"] = self.cover_image
        if self.description:
            epub["description"] = self.description
        if self.publisher:
            epub["publisher"] = self.publisher
        if self.rights:
            epub["rights"] = self.rights
        if self.identifier:
            epub["identifier"] = self.identifier
        if self.author:
            epub["creator"] = self.author
        if epub:
            document["format"] = {"epub": epub}
        return document


def _clean(value: object, limit: int) -> str:
    if value is None:
        return ""
    text = " ".join(str(value).split())
    return text[:limit].strip()


def _typst_safe(value: object, limit: int) -> str:
    """Text that will be spliced into the Typst show rule."""
    text = _clean(value, limit)
    return (
        text.replace("[", "(")
        .replace("]", ")")
        .replace("#", "")
        .replace("$", "")
        .replace('"', "'")
        .replace("\\", "")
        .strip()
    )


def _flatten_author(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return _typst_safe(value, 200)
    if isinstance(value, dict):
        return _typst_safe(value.get("name") or value.get("literal") or "", 200)
    if isinstance(value, list):
        names = [_flatten_author(item) for item in value]
        return ", ".join(name for name in names if name)[:200]
    return _typst_safe(value, 200)


def _mapping(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _lang(value: object) -> str:
    text = _clean(value, 16)
    if text and all(ch.isalnum() or ch == "-" for ch in text):
        return text
    return ""


def parse_quarto_yaml(text: str) -> BookMetadata:
    """Honor title, author, language, cover, and EPUB metadata. Ignore everything else."""
    if len(text.encode("utf-8")) > 32_000:
        raise MetadataError("_quarto.yml is too large")
    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise MetadataError("Could not read _quarto.yml") from exc
    if loaded is None:
        return BookMetadata()
    if not isinstance(loaded, dict):
        raise MetadataError("_quarto.yml must be a mapping")

    book = _mapping(loaded.get("book"))
    epub = _mapping(_mapping(loaded.get("format")).get("epub"))
    meta = BookMetadata()

    title = _typst_safe(book.get("title") or loaded.get("title") or "", 200)
    if title:
        meta.title = title
    subtitle = _typst_safe(book.get("subtitle") or loaded.get("subtitle") or "", 200)
    if subtitle:
        meta.subtitle = subtitle
    author = _flatten_author(book.get("author") if "author" in book else loaded.get("author"))
    if author:
        meta.author = author
    lang = _lang(loaded.get("lang") or book.get("lang") or epub.get("lang"))
    if lang:
        meta.lang = lang
    date = _typst_safe(book.get("date") or loaded.get("date") or epub.get("date") or "", 40)
    if date:
        meta.date = date

    cover = book.get("cover-image") or epub.get("cover-image") or loaded.get("cover-image") or ""
    meta.cover_image = _clean(cover, 180)
    meta.description = _clean(epub.get("description") or book.get("description") or "", 2000)
    meta.publisher = _clean(epub.get("publisher") or "", 200)
    rights = epub.get("rights") or epub.get("copyright") or ""
    meta.rights = _clean(rights, 500)
    identifier = epub.get("identifier") or epub.get("isbn") or ""
    meta.identifier = _clean(identifier, 80)
    return meta
