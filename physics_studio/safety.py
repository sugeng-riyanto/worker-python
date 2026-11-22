"""Authoring rules for bundles the renderer is willing to compile.

Raw executable markup stays rejected. Fenced divs such as ``::: {.givens}``
are ordinary Markdown and are allowed; the Gold Standard filter renders them.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

# Shortcodes, executable code cells, raw-block fences, off-project links, and
# embedded documents. Fenced divs (::: {.class}) do not match this pattern.
RISKY = re.compile(
    r"\{\{[<%]"
    r"|(?m:^\s*(?:`{3,}|~{3,})\s*\{)"
    r"|\]\(\s*(?:file:|/|\.\./)"
    r"|<\s*(?:script|iframe|object|embed)\b",
    re.IGNORECASE,
)

ASSET_SUFFIXES = {".png", ".jpg", ".jpeg", ".svg", ".css"}

_PART = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._-]{0,120}\Z")
_SVG_BAD = re.compile(
    r"<\s*script\b|<\s*foreignObject\b|<\s*iframe\b|javascript\s*:|\bon[a-z]+\s*=",
    re.IGNORECASE,
)
_CSS_BAD = re.compile(r"expression\s*\(|javascript\s*:|@import\b|behavior\s*:", re.IGNORECASE)


def risky_markup(text: str) -> bool:
    return RISKY.search(text) is not None


def safe_archive_path(name: str) -> PurePosixPath | None:
    """Return a relative path that cannot escape the project, or None."""
    if not name or "\\" in name or "\x00" in name:
        return None
    pure = PurePosixPath(name)
    if pure.is_absolute() or not pure.parts:
        return None
    if any(part in {"", ".", ".."} for part in pure.parts):
        return None
    if len(pure.parts) > 6:
        return None
    for part in pure.parts:
        if part != part.strip() or not _PART.fullmatch(part):
            return None
    return pure


def asset_rejected(suffix: str, data: bytes) -> str | None:
    if suffix == ".svg":
        try:
            text = data.decode("utf-8")
        except UnicodeError:
            return "SVG assets must be UTF-8 text"
        if _SVG_BAD.search(text):
            return "SVG scripts and event handlers are not supported"
    elif suffix == ".css":
        try:
            text = data.decode("utf-8")
        except UnicodeError:
            return "CSS assets must be UTF-8 text"
        if _CSS_BAD.search(text):
            return "CSS imports and script expressions are not supported"
    return None


def sanitize_generated_qmd(text: str) -> str:
    """Drop markup the worker would reject, keeping Gold Standard divs."""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    cleaned = re.sub(r"^```(?:markdown|qmd|md)?\s*\n", "", cleaned, count=1, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n```$", "", cleaned, count=1)
    cleaned = re.sub(r"```\{.*?\}.*?```", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"\{\{<.*?>\}\}", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(
        r"<\s*(?:script|iframe|object|embed)\b.*?>.*?<\s*/\s*(?:script|iframe|object|embed)\s*>",
        "",
        cleaned,
        flags=re.DOTALL | re.IGNORECASE,
    )
    cleaned = re.sub(r"\]\(\s*(?:file:|/|\.\./)[^)]*\)", "](#)", cleaned, flags=re.IGNORECASE)
    if cleaned.lstrip().startswith("---"):
        parts = cleaned.lstrip().split("\n---\n", 1)
        if len(parts) == 2:
            cleaned = parts[1]
    cleaned = cleaned.strip()
    return cleaned + ("\n" if cleaned else "")
