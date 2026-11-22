"""Render the sample chapter through ALL mode and check every product.

Starts the worker itself, so the same command runs on a host with Quarto or
inside the Docker image:

    QUARTO_WORKER_TOKEN=... python scripts/verify_sample.py --out /tmp/sample
"""

from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from physics_studio.config import Config  # noqa: E402
from physics_studio.worker import serve  # noqa: E402

SAMPLE = ROOT / "fixtures" / "sample_chapter"


def _zip_sample() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in SAMPLE.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(SAMPLE).as_posix())
    return buffer.getvalue()


def _request(base: str, method: str, path: str, token: str | None, body: bytes | None = None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        headers["Content-Type"] = "application/zip"
        headers["Content-Length"] = str(len(body))
    request = urllib.request.Request(base + path, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, response.read()


def _fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="out/sample")
    parser.add_argument("--timeout", type=int, default=int(os.environ.get("RENDER_TIMEOUT_SECONDS", "240")))
    args = parser.parse_args()
    token = os.environ.get("QUARTO_WORKER_TOKEN", "")
    if len(token) < 32:
        _fail("Set QUARTO_WORKER_TOKEN to at least 32 characters.")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    job_root = out / "jobs"
    config = Config(
        token=token,
        host="127.0.0.1",
        port=0,
        job_root=job_root,
        render_timeout=args.timeout,
        max_zip_bytes=24 * 1024 * 1024,
    )
    httpd = serve(config)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        _request(base, "GET", "/healthz", None)
        _status, created = _request(base, "POST", "/jobs/ALL", token, _zip_sample())
        job = json.loads(created)["job"]
        state = {}
        deadline = time.time() + args.timeout * 5 + 60
        while time.time() < deadline:
            _status, body = _request(base, "GET", f"/jobs/{job}", token)
            state = json.loads(body)
            if state["state"] in {"done", "failed"}:
                break
            time.sleep(1)
        if state.get("state") != "done":
            _fail("ALL render failed:\n" + json.dumps(state, indent=2))
        saved = {}
        for fmt, path in state["outputs"].items():
            _status, payload = _request(base, "GET", path, None)
            filename = path.rsplit("/", 1)[-1]
            target = out / filename
            target.write_bytes(payload)
            saved[fmt] = target
            print(f"{fmt}: {target} ({len(payload)} bytes)")
        _check(saved, out)
    finally:
        httpd.shutdown()
        httpd.server_close()
    print("sample chapter rendered in all five formats")


def _check(saved: dict[str, Path], out: Path) -> None:
    pdf = saved["PDF"].read_bytes()
    if not pdf.startswith(b"%PDF"):
        _fail("PDF is not a PDF")
    info = subprocess.run(["pdfinfo", str(saved["PDF"])], capture_output=True, text=True, check=False)
    if info.returncode != 0:
        _fail(info.stderr)
    pages = 0
    for line in info.stdout.splitlines():
        if line.startswith("Pages:"):
            pages = int(line.split()[1])
    if pages < 2:
        _fail(f"expected multiple PDF pages, found {pages}")
    text = subprocess.run(["pdftotext", str(saved["PDF"]), "-"], capture_output=True, text=True, check=False)
    for needle in ("Sugeng Riyanto", "G.I.V.E.N.S.", "Exam Trap", "Active Learning Workspace"):
        if needle not in text.stdout:
            _fail(f"PDF text is missing {needle!r}")
    images = subprocess.run(["pdfimages", "-list", str(saved["PDF"])], capture_output=True, text=True, check=False)
    image_lines = [line for line in images.stdout.splitlines() if line.strip() and not line.startswith("page")]
    if len(image_lines) < 2:
        _fail("PDF does not contain the sample images:\n" + images.stdout)
    fonts = subprocess.run(["pdffonts", str(saved["PDF"])], capture_output=True, text=True, check=False)
    if "Source Serif" not in fonts.stdout and "SourceSerif" not in fonts.stdout:
        _fail("PDF does not embed Source Serif 4:\n" + fonts.stdout)
    preview = out / "pdf-page-1.png"
    subprocess.run(["pdftoppm", "-png", "-f", "1", "-l", "1", "-r", "110", str(saved["PDF"]), str(out / "pdf-page")], check=True)
    produced = list(out.glob("pdf-page*.png"))
    if not produced:
        _fail("pdftoppm did not write a preview")
    if produced[0] != preview and not preview.exists():
        produced[0].replace(preview)

    with zipfile.ZipFile(saved["DOCX"]) as docx:
        document = docx.read("word/document.xml").decode("utf-8")
        styles = docx.read("word/styles.xml").decode("utf-8")
        media = [name for name in docx.namelist() if name.startswith("word/media/")]
    for style in ("GivensBox", "ExamTrap", "WorkspaceBox"):
        if style not in document or style not in styles:
            _fail(f"DOCX is missing the {style} style")
    if not media:
        _fail("DOCX did not embed the figure")

    html = saved["HTML"].read_text(encoding="utf-8", errors="replace")
    for css_class in ("givens", "exam-trap", "workspace"):
        if css_class not in html:
            _fail(f"HTML is missing .{css_class}")
    if "Vernier caliper" not in html:
        _fail("HTML is missing the figure caption")
    if 'src="images/' in html or "href=\"gold-boxes.css\"" in html:
        _fail("HTML still points at a relative asset")

    with zipfile.ZipFile(saved["EPUB"]) as epub:
        epub_text = "\n".join(
            epub.read(name).decode("utf-8", errors="replace")
            for name in epub.namelist()
            if name.endswith((".opf", ".xhtml", ".html", ".css"))
        )
    for needle in ("Sugeng Riyanto", "Physics Textbook Studio", "id", "exam-trap", "9780000000001"):
        if needle not in epub_text:
            _fail(f"EPUB is missing {needle!r}")

    flipbook = saved["FLIPBOOK"].read_text(encoding="utf-8", errors="replace")
    if f'data-page-count="{pages}"' not in flipbook:
        _fail(f"flipbook page count does not match the PDF ({pages})")
    if flipbook.count("data:image/jpeg;base64,") != pages:
        _fail("flipbook is missing an embedded page image")
    if "reveal" in flipbook.lower():
        _fail("flipbook still uses reveal.js")
    if "Next page" not in flipbook:
        _fail("flipbook has no page turn control")


if __name__ == "__main__":
    main()
