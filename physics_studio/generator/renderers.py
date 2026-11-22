"""Real Quarto rendering and the credential-free dry-run stand-in."""

from __future__ import annotations

import io
import tempfile
import zipfile
from pathlib import Path

from physics_studio.formats import FORMATS
from physics_studio.render import render_formats
from physics_studio.staging import stage_zip


def _zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("placeholder.txt", "dry-run")
    return buffer.getvalue()


class DryRenderer:
    """Stage the archive (so it must be legal) and return placeholder products."""

    def render(self, archive: bytes) -> dict[str, bytes]:
        with tempfile.TemporaryDirectory() as temporary:
            stage_zip(archive, Path(temporary))
        html = b"<!DOCTYPE html><html><body>dry-run chapter</body></html>"
        flipbook = b'<!DOCTYPE html><html><body data-page-count="1">dry-run flipbook</body></html>'
        return {
            "PDF": b"%PDF-1.4\n% dry-run\n%%EOF\n",
            "DOCX": _zip_bytes(),
            "HTML": html,
            "EPUB": _zip_bytes(),
            "FLIPBOOK": flipbook,
        }


class QuartoRenderer:
    def __init__(self, timeout: int = 240):
        self.timeout = timeout

    def render(self, archive: bytes) -> dict[str, bytes]:
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            stage_zip(archive, work)
            produced = render_formats(work, list(FORMATS), self.timeout)
            return {fmt: (work / "_output" / name).read_bytes() for fmt, name in produced.items()}
