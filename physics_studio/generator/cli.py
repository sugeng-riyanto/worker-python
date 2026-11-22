"""Command line for the chapter generator."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from physics_studio.generator.gemini import urllib_transport
from physics_studio.generator.llm import LLMError, build_client
from physics_studio.generator.mock import MockGemini
from physics_studio.generator.pipeline import GenerateRequest, run_job
from physics_studio.generator.renderers import DryRenderer, QuartoRenderer
from physics_studio.generator.storage import (
    DriveLibrary,
    LocalLibrary,
    LocalSheet,
    SheetTracker,
    fetch_google_doc,
    load_service_account,
)
from physics_studio.generator.toc import parse_toc


def _toc_text(args, credentials=None) -> str:
    if args.toc_text:
        return args.toc_text
    if args.toc_file:
        return Path(args.toc_file).read_text(encoding="utf-8")
    if args.toc_doc_id:
        if args.dry_run:
            raise SystemExit("Dry-run reads a local TOC. Pass --toc-file instead of --toc-doc-id.")
        if credentials is None:
            raise SystemExit("A service account is required to read a Google Doc.")
        return fetch_google_doc(credentials, args.toc_doc_id)
    raise SystemExit("Pass --toc-file, --toc-text, or --toc-doc-id.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate one textbook chapter and render all five formats.")
    parser.add_argument("--toc-file", help="Path to a pasted Master TOC")
    parser.add_argument("--toc-text", help="TOC text")
    parser.add_argument("--toc-doc-id", help="Google Doc id of the TOC")
    parser.add_argument("--book", help="A0 or Book A0")
    parser.add_argument("--chapter", type=int, help="Chapter number")
    parser.add_argument("--out", default="out/generator")
    parser.add_argument("--providers", default=None, help="Provider order, for example deepseek,gemini")
    parser.add_argument("--model", default=None, help="Model id, or a comma-separated fallback list")
    parser.add_argument("--dry-run", action="store_true", help="Use stand-ins instead of an LLM, Drive, and Sheets")
    parser.add_argument("--toc-only", action="store_true", help="Write toc.json and exit")
    parser.add_argument("--force", action="store_true", help="Generate again even if this chapter hash is done")
    parser.add_argument("--author", default=os.environ.get("BOOK_AUTHOR", "Academic Physics Publishing Team"))
    parser.add_argument("--lang", default=os.environ.get("BOOK_LANG", "id"))
    parser.add_argument("--publisher", default=os.environ.get("BOOK_PUBLISHER", "Physics Textbook Studio"))
    args = parser.parse_args(argv)

    out_dir = Path(args.out)
    credentials = None
    if not args.dry_run and (args.toc_doc_id or not args.toc_only):
        if not args.toc_only:
            credentials = load_service_account()
        elif args.toc_doc_id:
            credentials = load_service_account()
    text = _toc_text(args, credentials)
    toc = parse_toc(text)
    out_dir.mkdir(parents=True, exist_ok=True)
    toc_path = out_dir / "toc.json"
    toc_path.write_text(json.dumps(toc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.toc_only:
        json.dump({"toc": str(toc_path), "books": [book["id"] for book in toc["books"]]}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    if not args.book or args.chapter is None:
        raise SystemExit("--book and --chapter are required unless --toc-only is set.")

    if args.dry_run:
        gemini = MockGemini()
        library = LocalLibrary(out_dir / "drive")
        tracker = LocalSheet(out_dir / "sheet.json")
        renderer = DryRenderer()
    else:
        try:
            gemini = build_client(os.environ, urllib_transport, providers=args.providers, model=args.model)
        except LLMError as exc:
            raise SystemExit(str(exc)) from exc
        if credentials is None:
            credentials = load_service_account()
        library = DriveLibrary(
            credentials,
            root_folder_id=os.environ.get("DRIVE_ROOT_FOLDER_ID", "").strip(),
            root_name=os.environ.get("DRIVE_ROOT_FOLDER_NAME", "").strip(),
        )
        sheet_id = os.environ.get("SHEET_ID", "").strip()
        if not sheet_id:
            raise SystemExit("Set SHEET_ID to the tracking spreadsheet.")
        tracker = SheetTracker(credentials, sheet_id)
        renderer = QuartoRenderer(timeout=int(os.environ.get("RENDER_TIMEOUT_SECONDS", "240")))

    try:
        result = run_job(
            GenerateRequest(
                toc_text=text,
                book=args.book,
                chapter=args.chapter,
                out_dir=out_dir,
                author=args.author,
                lang=args.lang,
                publisher=args.publisher,
                expand=not args.dry_run,
                force=args.force,
            ),
            gemini,
            library,
            tracker,
            renderer,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0
