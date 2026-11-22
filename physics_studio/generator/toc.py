"""Parse the two Master TOC shapes into structured JSON.

Series A uses ``Chapter N: ... (NN pp.)`` followed by numbered subsections
(``1.1 ...``). Series B and C put the syllabus note on the chapter line
(``Chapter N: ... (NN pp.) — ...``) and do not list numbered subsections.
"""

from __future__ import annotations

import re

BOOK_RE = re.compile(
    r"^Book\s+([ABC][012])\s+[—–-]\s+(.+?)\s+\((\d+)\s+Pages?\)\s*$",
    re.IGNORECASE,
)
CURRICULUM_RE = re.compile(r"^Curriculum Pairing:\s*(.+?)\s*$", re.IGNORECASE)
CHAPTER_RE = re.compile(
    r"^Chapter\s+(\d+)\s*:\s*(.+?)\s+\((\d+)\s*pp\.\)\s*(?:[—–-]\s*(.*))?$",
    re.IGNORECASE,
)
SUBSECTION_RE = re.compile(r"^(\d+\.\d+)\s+(\S.*)$")
MATTER_RE = re.compile(
    r"^(?!Chapter\s)(.+?)\s+\((\d+)\s*pp\.\)\s*:?\s*(.*)$",
    re.IGNORECASE,
)


class TocError(ValueError):
    """The table of contents could not be structured."""


def parse_toc(text: str) -> dict:
    books: list[dict] = []
    current: dict | None = None
    chapter: dict | None = None

    def finish_chapter() -> None:
        nonlocal chapter
        if current is not None and chapter is not None:
            current["chapters"].append(chapter)
        chapter = None

    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        book_match = BOOK_RE.match(line)
        if book_match:
            finish_chapter()
            code = book_match.group(1).upper()
            current = {
                "id": code,
                "code": f"Book {code}",
                "title": " ".join(book_match.group(2).split()),
                "pages": int(book_match.group(3)),
                "curriculum": "",
                "front_matter": None,
                "back_matter": [],
                "chapters": [],
            }
            books.append(current)
            chapter = None
            continue
        if current is None:
            continue
        curriculum_match = CURRICULUM_RE.match(line)
        if curriculum_match:
            current["curriculum"] = " ".join(curriculum_match.group(1).split())
            continue
        chapter_match = CHAPTER_RE.match(line)
        if chapter_match:
            finish_chapter()
            notes = chapter_match.group(4) or ""
            chapter = {
                "number": int(chapter_match.group(1)),
                "title": " ".join(chapter_match.group(2).split()),
                "pages": int(chapter_match.group(3)),
                "notes": " ".join(notes.split()),
                "subsections": [],
            }
            continue
        subsection_match = SUBSECTION_RE.match(line)
        if subsection_match and chapter is not None:
            number = subsection_match.group(1)
            major = int(number.split(".", 1)[0])
            if major != chapter["number"]:
                raise TocError(
                    f"Subsection {number} does not belong to chapter {chapter['number']}"
                )
            chapter["subsections"].append(
                {"number": number, "title": " ".join(subsection_match.group(2).split())}
            )
            continue
        matter_match = MATTER_RE.match(line)
        if matter_match:
            finish_chapter()
            title = " ".join(matter_match.group(1).split())
            item = {
                "title": title,
                "pages": int(matter_match.group(2)),
                "notes": " ".join((matter_match.group(3) or "").split()),
            }
            if title.lower().startswith("front"):
                current["front_matter"] = item
            else:
                current["back_matter"].append(item)
            continue
    finish_chapter()
    if not books:
        raise TocError("No books found. Expected lines like 'Book A0 — … (450 Pages)'.")
    return {"books": books}


def find_book(toc: dict, code: str) -> dict:
    token = code.strip().upper().replace("BOOK", "").strip()
    for book in toc["books"]:
        if book["id"] == token or book["code"].upper() == code.strip().upper():
            return book
    known = ", ".join(book["id"] for book in toc["books"])
    raise TocError(f"Unknown book {code!r}. Known books: {known}")


def find_chapter(book: dict, number: int) -> dict:
    for chapter in book["chapters"]:
        if chapter["number"] == number:
            return chapter
    raise TocError(f"{book['code']} has no chapter {number}")
