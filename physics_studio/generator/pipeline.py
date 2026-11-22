"""Generate one chapter, render all five formats, and record the job."""

from __future__ import annotations

import io
import json
import re
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from physics_studio.generator.qmd import (
    assemble_chapter,
    complete_unit,
    content_hash,
    system_prompt,
    unit_prompt,
    units_for,
)
from physics_studio.generator.toc import find_book, find_chapter, parse_toc
from physics_studio.metadata import BookMetadata
from physics_studio.safety import risky_markup

FORMAT_EXTENSIONS = {
    "PDF": "pdf",
    "DOCX": "docx",
    "HTML": "html",
    "EPUB": "epub",
    "FLIPBOOK": "html",
}


@dataclass
class GenerateRequest:
    toc_text: str
    book: str
    chapter: int
    out_dir: Path
    author: str = "Academic Physics Publishing Team"
    lang: str = "id"
    publisher: str = "Physics Textbook Studio"
    expand: bool = True
    force: bool = False


def _slug(chapter_number: int, title: str, extension: str) -> str:
    words = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40].strip("-")
    stem = f"c{chapter_number:02d}-{words}" if words else f"c{chapter_number:02d}"
    return f"{stem}.{extension}"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _archive(chapter: dict, qmd: str, metadata: BookMetadata) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"bab-{int(chapter['number']):02d}.qmd", qmd)
        archive.writestr(
            "index.qmd",
            f"# Preface {{.unnumbered}}\n\n{metadata.title}\n",
        )
        archive.writestr(
            "_quarto.yml",
            yaml.safe_dump(metadata.as_yaml_document(), allow_unicode=True, sort_keys=False),
        )
    return buffer.getvalue()


def _row(job_id: str, digest: str, book: dict, chapter: dict, status: str, attempts: int, error: str, links: dict) -> dict:
    return {
        "job_id": job_id,
        "content_hash": digest,
        "book": book["code"],
        "chapter": chapter["number"],
        "status": status,
        "attempts": attempts,
        "error": error,
        "output_links": links,
        "updated_at": _now(),
    }


def run_job(request: GenerateRequest, gemini, library, tracker, renderer) -> dict:
    toc = parse_toc(request.toc_text)
    request.out_dir.mkdir(parents=True, exist_ok=True)
    (request.out_dir / "toc.json").write_text(
        json.dumps(toc, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    book = find_book(toc, request.book)
    chapter = find_chapter(book, request.chapter)
    units = units_for(chapter)
    digest = content_hash(book, chapter, units)
    existing = tracker.find(digest)
    if existing and existing.get("status") == "done" and not request.force:
        return {
            "idempotent": True,
            "job_id": existing["job_id"],
            "status": "done",
            "attempts": existing["attempts"],
            "content_hash": digest,
            "book": book["code"],
            "chapter": chapter["number"],
            "outputs": existing.get("output_links") or {},
            "error": "",
            "toc": str(request.out_dir / "toc.json"),
        }

    attempts = int(existing["attempts"]) + 1 if existing else 1
    job_id = existing["job_id"] if existing else uuid.uuid4().hex
    tracker.save(_row(job_id, digest, book, chapter, "running", attempts, "", {}))
    try:
        system = system_prompt(book)
        sections: list[tuple[str, str]] = []
        for unit in units:
            body = complete_unit(
                gemini,
                system,
                unit_prompt(book, chapter, unit),
                unit.words,
                request.expand,
            )
            sections.append((unit.title, body))
        qmd = assemble_chapter(chapter, sections)
        if risky_markup(qmd):
            raise RuntimeError("Generated chapter still contains markup the renderer rejects")
        qmd_path = request.out_dir / f"book-{book['id'].lower()}-c{int(chapter['number']):02d}.qmd"
        qmd_path.write_text(qmd, encoding="utf-8")
        metadata = BookMetadata(
            title=chapter["title"],
            author=request.author,
            lang=request.lang,
            publisher=request.publisher,
            description=f"{book['code']} chapter {chapter['number']}: {chapter['title']}",
            rights=f"Copyright {request.publisher}",
        )
        outputs = renderer.render(_archive(chapter, qmd, metadata))
        links = {}
        for fmt, data in outputs.items():
            extension = FORMAT_EXTENSIONS[fmt]
            filename = _slug(int(chapter["number"]), chapter["title"], extension)
            links[fmt.lower()] = library.upload(book["code"], fmt.lower(), filename, data)
        tracker.save(_row(job_id, digest, book, chapter, "done", attempts, "", links))
        return {
            "idempotent": False,
            "job_id": job_id,
            "status": "done",
            "attempts": attempts,
            "content_hash": digest,
            "book": book["code"],
            "chapter": chapter["number"],
            "outputs": links,
            "error": "",
            "qmd": str(qmd_path),
            "toc": str(request.out_dir / "toc.json"),
        }
    except Exception as exc:
        message = str(exc).strip() or exc.__class__.__name__
        tracker.save(_row(job_id, digest, book, chapter, "failed", attempts, message[:2000], {}))
        raise
