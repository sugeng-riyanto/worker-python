"""Turn an uploaded zip into a Quarto book project with a fixed, safe configuration."""

from __future__ import annotations

import io
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

import yaml

from physics_studio.metadata import THEMES, BookMetadata, MetadataError, parse_quarto_yaml
from physics_studio.palettes import SCREEN_ONLY, css_vars, resolve, typst_dict
from physics_studio.safety import (
    ASSET_SUFFIXES,
    asset_rejected,
    risky_markup,
    safe_archive_path,
)

ASSETS = Path(__file__).resolve().parent / "assets"

STAGED_ASSETS = ("typst-show.typ", "textbook.lua", "gold-boxes.lua", "gold-boxes.css", "textbook.css")
DEFAULT_FONT_DIR = Path("/usr/local/share/fonts/textbook")
FONT_LINK = "_fonts"
FONT_CSS = "textbook-fonts.css"
PALETTE_CSS = "textbook-palette.css"
# (file, family, weight, style) embedded into the single-file HTML.
_WEB_FONTS = (
    ("SourceSans3-Regular.woff2", "Source Sans 3", 400, "normal"),
    ("SourceSans3-It.woff2", "Source Sans 3", 400, "italic"),
    ("SourceSans3-Bold.woff2", "Source Sans 3", 700, "normal"),
    ("BarlowCondensed-Bold.ttf", "Barlow Condensed", 700, "normal"),
)

_CHAPTER_NAME = re.compile(r"^(?:bab|chapter)-(\d+)\.qmd\Z", re.IGNORECASE)


class StagingError(ValueError):
    """The archive cannot be rendered. The message is safe to return to the client."""


@dataclass
class Limits:
    max_zip_bytes: int = 24 * 1024 * 1024
    max_uncompressed_bytes: int = 48 * 1024 * 1024
    max_asset_bytes: int = 8 * 1024 * 1024
    max_qmd_bytes: int = 2 * 1024 * 1024
    max_files: int = 300


@dataclass
class StagedBook:
    metadata: BookMetadata
    chapters: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)


def _chapter_key(name: str) -> tuple:
    match = _CHAPTER_NAME.match(name)
    if match:
        return (0, int(match.group(1)), name.lower())
    return (1, 0, name.lower())


def _read_zip(raw: bytes, limits: Limits) -> ZipFile:
    if not raw:
        raise StagingError("Archive is empty")
    if len(raw) > limits.max_zip_bytes:
        raise StagingError("Archive is too large")
    try:
        archive = ZipFile(io.BytesIO(raw))
    except BadZipFile as exc:
        raise StagingError("Archive is not a valid zip file") from exc
    return archive


def stage_zip(raw: bytes, work: Path, limits: Limits | None = None) -> StagedBook:
    """Validate ``raw`` and write a Quarto project into ``work``.

    ``index.qmd`` and ``flipbook/flipbook.qmd`` are optional. Image and CSS
    assets are kept when their paths stay inside the project. The caller's
    ``_quarto.yml`` contributes metadata only; execution, filters, and output
    paths from that file are not used.
    """
    limits = limits or Limits()
    work.mkdir(parents=True, exist_ok=True)
    archive = _read_zip(raw, limits)
    try:
        return _stage_open(archive, work, limits)
    finally:
        archive.close()


def _stage_open(archive: ZipFile, work: Path, limits: Limits) -> StagedBook:
    infos = [info for info in archive.infolist() if not info.is_dir()]
    if len(infos) > limits.max_files:
        raise StagingError("Archive has too many files")
    if sum(info.file_size for info in infos) > limits.max_uncompressed_bytes:
        raise StagingError("Uncompressed source is too large")

    metadata = BookMetadata()
    chapters: list[tuple[str, str]] = []
    index_text: str | None = None
    assets: list[tuple[PurePosixPath, bytes]] = []
    seen: set[str] = set()

    for info in infos:
        if info.filename == "_quarto.yml":
            relative = PurePosixPath("_quarto.yml")
        else:
            relative = safe_archive_path(info.filename)
            if relative is None:
                raise StagingError(f"Unsafe path in archive: {info.filename!r}")
        posix = relative.as_posix()
        if posix in seen:
            raise StagingError(f"Duplicate path in archive: {posix}")
        seen.add(posix)
        payload = archive.read(info)

        if posix == "_quarto.yml":
            try:
                metadata = parse_quarto_yaml(payload.decode("utf-8"))
            except UnicodeError as exc:
                raise StagingError("_quarto.yml must be UTF-8") from exc
            except MetadataError as exc:
                raise StagingError(str(exc)) from exc
            continue

        if posix == "flipbook/flipbook.qmd":
            # Kept for old Apps Script bundles. The flipbook is built from the PDF.
            continue

        suffix = relative.suffix.lower()
        if suffix == ".qmd":
            if len(relative.parts) != 1:
                raise StagingError("Chapter files must sit in the archive root")
            if len(payload) > limits.max_qmd_bytes:
                raise StagingError(f"{posix} is too large")
            try:
                text = payload.decode("utf-8")
            except UnicodeError as exc:
                raise StagingError(f"{posix} must be UTF-8") from exc
            if risky_markup(text):
                raise StagingError("Active source directives are not supported")
            if posix == "index.qmd":
                index_text = text
            else:
                if text.lstrip().startswith("---"):
                    raise StagingError("Chapter front matter is not supported")
                chapters.append((posix, text))
            continue

        if suffix in ASSET_SUFFIXES:
            if len(payload) > limits.max_asset_bytes:
                raise StagingError(f"{posix} exceeds the asset size limit")
            reason = asset_rejected(suffix, payload)
            if reason:
                raise StagingError(f"{posix}: {reason}")
            assets.append((relative, payload))
            continue

        raise StagingError(f"Unsupported file in archive: {posix}")

    if not chapters:
        raise StagingError("Archive needs at least one chapter .qmd file")
    if len(chapters) > 80:
        raise StagingError("Too many chapters")

    if metadata.cover_image:
        cover = safe_archive_path(metadata.cover_image)
        names = {path.as_posix() for path, _ in assets}
        if cover is None or cover.as_posix() not in names:
            raise StagingError("Cover image from _quarto.yml is not in the archive")
        if cover.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            raise StagingError("Cover image must be a PNG or JPEG")

    chapters.sort(key=lambda item: _chapter_key(item[0]))
    for name, text in chapters:
        destination = work / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")
    if index_text is None:
        index_text = (
            "# Preface {.unnumbered}\n\n"
            "This volume was assembled by Physics Textbook Studio.\n"
        )
    (work / "index.qmd").write_text(index_text, encoding="utf-8")

    css_files = ["gold-boxes.css", "textbook.css"]
    for relative, payload in assets:
        destination = work / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        if relative.suffix.lower() == ".css":
            css_files.append(relative.as_posix())

    for asset_name in STAGED_ASSETS:
        shutil.copy2(ASSETS / asset_name, work / asset_name)
    palette = _palette_name(metadata)
    _apply_palette(work, palette)

    css_files.insert(2, PALETTE_CSS)
    html_css = list(css_files)
    if _link_fonts(work) and _write_font_css(work):
        html_css.insert(0, FONT_CSS)
    _write_project_yaml(work, metadata, [name for name, _ in chapters], css_files, html_css)
    return StagedBook(
        metadata=metadata,
        chapters=[name for name, _ in chapters],
        assets=[path.as_posix() for path, _ in assets],
    )


def _write_project_yaml(
    work: Path,
    metadata: BookMetadata,
    chapters: list[str],
    css_files: list[str],
    html_css: list[str] | None = None,
) -> None:
    book: dict = {
        "title": metadata.title,
        "author": metadata.author,
        "output-file": "physics",
        "chapters": ["index.qmd", *chapters],
    }
    if metadata.subtitle:
        book["subtitle"] = metadata.subtitle
    if metadata.date:
        book["date"] = metadata.date
    if metadata.cover_image:
        book["cover-image"] = metadata.cover_image

    epub: dict = {"toc": True, "css": list(css_files)}
    if metadata.cover_image:
        epub["cover-image"] = metadata.cover_image
    if metadata.description:
        epub["description"] = metadata.description
    if metadata.publisher:
        epub["publisher"] = metadata.publisher
    if metadata.rights:
        epub["rights"] = metadata.rights
    if metadata.identifier:
        epub["identifier"] = metadata.identifier
    if metadata.author:
        epub["creator"] = metadata.author
    if metadata.date:
        epub["date"] = metadata.date

    typst: dict = {
        "papersize": "iso-b5",
        "template-partials": ["typst-show.typ"],
    }
    if (work / FONT_LINK).is_symlink() or _link_fonts(work):
        # Quarto resolves font-paths against the project directory.
        typst["font-paths"] = [FONT_LINK]

    document = {
        "project": {"type": "book", "output-dir": "_render"},
        "book": book,
        "lang": metadata.lang,
        "execute": {"enabled": False},
        "toc": True,
        "crossref": {"chapters": True},
        "bc-theme": _theme_name(metadata),
        "bc-palette": _palette_name(metadata),
        "filters": ["textbook.lua", "gold-boxes.lua"],
        "format": {
            "typst": typst,
            "docx": {"reference-doc": "b5-reference.docx", "toc": True},
            "html": {
                "theme": "darkly" if _palette_name(metadata) in SCREEN_ONLY else "cosmo",
                "css": list(html_css or css_files),
                "embed-resources": True,
                "toc": True,
            },
            "epub": epub,
        },
    }
    (work / "_quarto.yml").write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _theme_name(metadata: BookMetadata) -> str:
    """``studio`` (default) or ``classic``; PHYSICS_THEME sets the worker default."""
    if metadata.theme:
        return metadata.theme
    fallback = os.environ.get("PHYSICS_THEME", "").strip().lower()
    return fallback if fallback in THEMES else "studio"


def _palette_name(metadata: BookMetadata) -> str:
    """Palette from the book (bc-palette / book.palette), else PHYSICS_PALETTE, else the theme's own."""
    if metadata.palette:
        return metadata.palette
    fallback = os.environ.get("PHYSICS_PALETTE", "").strip().lower()
    return resolve(fallback, _theme_name(metadata))


_PALETTE_BLOCK = re.compile(r"// <bc-palette>.*?// </bc-palette>", re.DOTALL)


def _apply_palette(work: Path, palette: str) -> None:
    """Write the chosen palette into the staged Typst partial and the palette CSS."""
    show = work / "typst-show.typ"
    text = show.read_text(encoding="utf-8")
    block = "// <bc-palette>\n" + typst_dict(palette) + "// </bc-palette>"
    text, count = _PALETTE_BLOCK.subn(lambda _: block, text, count=1)
    if count != 1:
        raise StagingError("typst-show.typ is missing its palette block")
    show.write_text(text, encoding="utf-8")
    (work / PALETTE_CSS).write_text(css_vars(palette), encoding="utf-8")


def font_dir() -> Path | None:
    """Static textbook fonts. Variable fonts render poorly in Typst, so use these first."""
    configured = os.environ.get("PHYSICS_FONT_DIR", "").strip()
    path = Path(configured) if configured else DEFAULT_FONT_DIR
    return path if path.is_dir() else None


def _link_fonts(work: Path) -> bool:
    source = font_dir()
    if source is None:
        return False
    link = work / FONT_LINK
    if link.is_symlink():
        return True
    if link.exists():
        return False
    try:
        link.symlink_to(source.resolve(), target_is_directory=True)
    except OSError:
        shutil.copytree(source, link)
    return True


def _write_font_css(work: Path) -> bool:
    """@font-face rules for the HTML so it looks the same without installed fonts."""
    if not (work / FONT_LINK).is_symlink():
        return False
    rules = []
    for filename, family, weight, style in _WEB_FONTS:
        if not (work / FONT_LINK / filename).is_file():
            continue
        fmt = {".woff2": "woff2", ".otf": "opentype"}.get(Path(filename).suffix, "truetype")
        rules.append(
            "@font-face { "
            f'font-family: "{family}"; font-weight: {weight}; font-style: {style}; '
            f'src: url("{FONT_LINK}/{filename}") format("{fmt}"); font-display: swap; }}'
        )
    if not rules:
        return False
    (work / FONT_CSS).write_text("\n".join(rules) + "\n", encoding="utf-8")
    return True
