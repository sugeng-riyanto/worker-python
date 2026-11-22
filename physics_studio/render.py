"""Render a staged Quarto project to one or more products."""

from __future__ import annotations

import base64
import mimetypes
import os
import re
import shutil
import subprocess
from pathlib import Path

from physics_studio.flipbook import write_flipbook
from physics_studio.formats import FILENAMES, QUARTO_TARGETS
from physics_studio.reference_docx import write_reference
from physics_studio.render_error import RenderError

_PASS_ENV = {
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "XDG_CACHE_HOME",
    "XDG_DATA_HOME",
    "XDG_CONFIG_HOME",
    "FONTCONFIG_PATH",
    "FONTCONFIG_FILE",
    "TMPDIR",
    "TEMP",
    "TMP",
    "USER",
    "LOGNAME",
    "QUARTO_PATH",
}
_SECRET_MARKERS = ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "KEY", "JSON")


def render_env(source: dict[str, str] | None = None) -> dict[str, str]:
    """Environment for Quarto. Worker tokens and API keys are not forwarded."""
    source = os.environ if source is None else source
    env: dict[str, str] = {}
    for name, value in source.items():
        if name not in _PASS_ENV:
            continue
        if any(marker in name for marker in _SECRET_MARKERS):
            continue
        env[name] = value
    env.setdefault("PATH", source.get("PATH", "/usr/bin:/bin"))
    env.setdefault("HOME", str(Path.home()))
    env.setdefault("LANG", "C.UTF-8")
    return env


def tail(text: str, limit: int = 3500) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return "…\n" + cleaned[-limit:]


def _quarto_binary() -> str:
    quarto = os.environ.get("QUARTO_PATH") or shutil.which("quarto")
    if not quarto:
        raise RenderError("Quarto CLI is not installed or not on PATH.")
    return quarto


def _run(cmd: list[str], cwd: Path, env: dict[str, str], timeout: int, label: str) -> None:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        detail = ""
        if isinstance(exc.stderr, str):
            detail = exc.stderr
        raise RenderError(f"{label} timed out after {timeout}s.\n{tail(detail)}") from exc
    except OSError as exc:
        raise RenderError(f"{label} could not be started: {exc}") from exc
    if proc.returncode != 0:
        detail = tail((proc.stderr or "") + "\n" + (proc.stdout or ""))
        raise RenderError(f"{label} failed.\n{detail}")


def _collect(project: Path, suffixes: tuple[str, ...], prefer: str) -> Path:
    roots = [project / "_render", project]
    found: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if "_output" in path.parts or "_pages" in path.parts:
                continue
            if path.suffix.lower() in suffixes:
                found.append(path)
    if not found:
        raise RenderError(f"Render finished without a {prefer} file.")
    preferred = [path for path in found if path.name == prefer]
    pool = preferred or found
    return max(pool, key=lambda path: path.stat().st_size)


_ATTR = re.compile(r"""\b(src|href)\s*=\s*(["'])([^"']+)\2""", re.IGNORECASE)
_CSS_URL = re.compile(r"""url\(\s*(['"]?)([^'")]+)\1\s*\)""", re.IGNORECASE)


def _data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _local_target(base: Path, url: str) -> Path | None:
    if url.startswith(("data:", "http://", "https://", "mailto:", "#", "//")):
        return None
    relative = url.split("#", 1)[0].split("?", 1)[0]
    if not relative or relative.startswith("/"):
        return None
    target = (base / relative).resolve()
    try:
        target.relative_to(base.resolve())
    except ValueError:
        return None
    if not target.is_file() or target.stat().st_size > 8 * 1024 * 1024:
        return None
    return target


def _inline_css(css_text: str, base: Path) -> str:
    def replace(match: re.Match[str]) -> str:
        target = _local_target(base, match.group(2).strip())
        if target is None:
            return match.group(0)
        return f"url({_data_uri(target)})"

    return _CSS_URL.sub(replace, css_text)


def _html_sort_key(path: Path) -> tuple:
    stem = path.stem
    if stem == "index":
        return (0, 0, stem)
    match = re.match(r"(?:bab|chapter)-(\d+)$", stem, re.IGNORECASE)
    if match:
        return (1, int(match.group(1)), stem.lower())
    return (2, 0, stem.lower())


def _main_fragment(text: str, anchor: str) -> str | None:
    start = text.find("<main")
    end = text.find("</main>")
    if start < 0 or end < 0:
        return None
    fragment = text[start : end + len("</main>")]
    if not re.match(r"<main[^>]*\sid=", fragment):
        fragment = fragment.replace("<main", f'<main id="{anchor}"', 1)
    return fragment


def combine_book_html(render_dir: Path) -> str:
    """Quarto books emit one HTML file per chapter. Join them so one signed link works offline."""
    pages = sorted(
        (path for path in render_dir.glob("*.html") if path.is_file()),
        key=_html_sort_key,
    )
    if not pages:
        raise RenderError("HTML render finished without a page.")
    fragments: list[str] = []
    anchors: dict[str, str] = {}
    for page in pages:
        anchor = "part-" + re.sub(r"[^A-Za-z0-9_-]", "-", page.stem)
        anchors[page.stem] = anchor
        fragment = _main_fragment(page.read_text(encoding="utf-8", errors="replace"), anchor)
        if fragment:
            fragments.append(fragment)
    if not fragments:
        raise RenderError("HTML render did not contain chapter content.")
    shell_path = max(pages, key=lambda path: path.stat().st_size)
    shell = shell_path.read_text(encoding="utf-8", errors="replace")
    start = shell.find("<main")
    end = shell.find("</main>")
    if start < 0 or end < 0:
        combined = shell
    else:
        combined = shell[:start] + "\n".join(fragments) + shell[end + len("</main>") :]

    def retarget(match: re.Match[str]) -> str:
        target = match.group(1).split("#", 1)[0].split("?", 1)[0]
        stem = Path(target).stem
        if stem in anchors:
            return f'href="#{anchors[stem]}"'
        return match.group(0)

    return re.sub(r'href="(?:\./)?([^"#?]+\.html)(?:[?#][^"]*)?"', retarget, combined)


def embed_local_assets(html_path: Path) -> None:
    """Inline local images and stylesheets so one signed URL can serve the HTML."""

    def replace_attr(match: re.Match[str]) -> str:
        attr, quote, url = match.group(1), match.group(2), match.group(3)
        target = _local_target(html_path.parent, url)
        if target is None:
            return match.group(0)
        if attr.lower() == "href" and target.suffix.lower() == ".css":
            css = _inline_css(target.read_text(encoding="utf-8", errors="replace"), target.parent)
            # Close the original link tag and follow it with a real style element.
            return f"data-embedded={quote}1{quote}></link><style>{css}</style><link data-removed={quote}"
        return f"{attr}={quote}{_data_uri(target)}{quote}"

    text = html_path.read_text(encoding="utf-8")
    html_path.write_text(_ATTR.sub(replace_attr, text), encoding="utf-8")


def render_formats(project: Path, formats: list[str], timeout: int) -> dict[str, str]:
    """Render ``formats`` into ``project/_output`` and return format -> filename."""
    quarto = _quarto_binary()
    env = render_env()
    output = project / "_output"
    output.mkdir(parents=True, exist_ok=True)
    produced: dict[str, str] = {}
    need_pdf = "PDF" in formats or "FLIPBOOK" in formats
    ordered = [fmt for fmt in ("PDF", "DOCX", "HTML", "EPUB") if fmt in formats or (fmt == "PDF" and need_pdf)]
    # Preserve a stable order and render PDF once even when only the flipbook was requested.
    seen: list[str] = []
    for fmt in ordered:
        if fmt not in seen:
            seen.append(fmt)

    pdf_path: Path | None = None
    for fmt in seen:
        if fmt == "DOCX":
            write_reference(project / "b5-reference.docx", quarto, env)
        _run([quarto, "render", "--to", QUARTO_TARGETS[fmt]], project, env, timeout, f"{fmt} render")
        suffix = {"PDF": (".pdf",), "DOCX": (".docx",), "HTML": (".html",), "EPUB": (".epub",)}[fmt]
        destination = output / FILENAMES[fmt]
        if fmt == "HTML":
            destination.write_text(combine_book_html(project / "_render"), encoding="utf-8")
            embed_local_assets(destination)
        else:
            source = _collect(project, suffix, FILENAMES[fmt])
            shutil.copy2(source, destination)
        if fmt == "PDF":
            pdf_path = destination
        if fmt in formats:
            produced[fmt] = destination.name

    if "FLIPBOOK" in formats:
        if pdf_path is None or not pdf_path.is_file():
            raise RenderError("Flipbook render could not find the PDF pages.")
        title = _book_title(project)
        lang = _book_lang(project)
        destination = output / FILENAMES["FLIPBOOK"]
        write_flipbook(pdf_path, destination, title=title, lang=lang, timeout=timeout)
        produced["FLIPBOOK"] = destination.name
    return produced


def _book_title(project: Path) -> str:
    text = (project / "_quarto.yml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^  title:\s*[\'"]?(.*?)[\'"]?\s*$', text)
    return match.group(1).strip() if match else "Physics Textbook Studio"


def _book_lang(project: Path) -> str:
    text = (project / "_quarto.yml").read_text(encoding="utf-8")
    match = re.search(r"(?m)^lang:\s*(\S+)\s*$", text)
    return match.group(1).strip("'\"") if match else "id"
