"""Turn an uploaded zip into a Quarto book project with a fixed, safe configuration."""

from __future__ import annotations

import io
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

import yaml

from physics_studio.metadata import BookMetadata, MetadataError, parse_quarto_yaml
from physics_studio.safety import (
    ASSET_SUFFIXES,
    asset_rejected,
    risky_markup,
    safe_archive_path,
)

ASSETS = Path(__file__).resolve().parent / "assets"

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

    css_files = ["gold-boxes.css"]
    for relative, payload in assets:
        destination = work / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        if relative.suffix.lower() == ".css":
            css_files.append(relative.as_posix())

    for asset_name in ("typst-show.typ", "gold-boxes.lua", "gold-boxes.css"):
        shutil.copy2(ASSETS / asset_name, work / asset_name)

    _write_project_yaml(work, metadata, [name for name, _ in chapters], css_files)
    return StagedBook(
        metadata=metadata,
        chapters=[name for name, _ in chapters],
        assets=[path.as_posix() for path, _ in assets],
    )


def _write_project_yaml(work: Path, metadata: BookMetadata, chapters: list[str], css_files: list[str]) -> None:
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

    document = {
        "project": {"type": "book", "output-dir": "_render"},
        "book": book,
        "lang": metadata.lang,
        "execute": {"enabled": False},
        "toc": True,
        "filters": ["gold-boxes.lua"],
        "format": {
            "typst": {
                "papersize": "iso-b5",
                "template-partials": ["typst-show.typ"],
            },
            "docx": {"reference-doc": "b5-reference.docx", "toc": True},
            "html": {
                "theme": "cosmo",
                "css": list(css_files),
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
