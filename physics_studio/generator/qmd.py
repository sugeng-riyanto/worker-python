"""Turn a parsed chapter into Quarto Markdown that uses Gold Standard divs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from physics_studio.safety import sanitize_generated_qmd

PROMPT_VERSION = "gold-2"
WORDS_PER_PAGE = 320

MANDATORY_MODULES = (
    "Chapter opener and dual-curriculum objectives",
    "Pedagogical header and coherent prose",
    "Inline active learning workspace",
    "Abstract-to-concrete practical bridge",
    "G.I.V.E.N.S. problem-solving protocol",
    "Exemplar worked example and mark scheme",
    "Checkpoint of common mistakes and exam traps",
    "High-yield equation and trap matrix",
    "Tiered practice and worked solutions",
    "Self-diagnostic and teacher attainment rubric",
)

BOX_GUIDE = """Write Quarto markdown in English. Use these fenced divs where they belong, and no other special syntax.
Command words: use the command word of each learning objective (state, define, describe, explain,
calculate, determine, sketch, plot, compare, evaluate, deduce, suggest, predict, design, investigate),
and vary them across tasks; do not reduce every activity to predict-observe-explain.
Problem-solving scaffolds: choose the ones that suit the content, never all of them. Each is a
multi-line fenced div (opening ::: {.class} line, content, closing ::: line):
- .guess: calculations; Given, Unknown, Equation, Substitute, Solve as a bullet list
- .free-body: forces; five steps to draw and use a free-body diagram
- .cer: investigations and arguments; Claim, Evidence, Reasoning
- .ideal: multi-step or design problems; .data-analysis: tables and graphs (with a graph-paper div)
- .error-analysis: a wrong worked line to correct; .estimate-check: estimate first, then check
- .think-pair-share, .concept-map, .real-world, .poe (Predict-Observe-Explain only where a demo fits)
- .givens: G (Given), I (Identify), V (Visualize), E (Equation), N/S (Numbers and sanity check)
- .exam-trap: the mistaken step, then the accurate reasoning
Pictures: ::: {.figure-frame height="45mm" caption="..."} with what the illustrator must draw, then :::
Plotting: ::: {.graph-paper width="110mm" height="70mm" x-label="t / s" y-label="v / m s⁻¹" x-max="5" y-max="10"} then :::
Teacher verification at the end of the chapter, one line per objective with its assessment objective and Bloom level:
::: {.teacher-verification}
- [ ] AO2 · Apply: Calculates acceleration from velocity-time data.
:::
Math: inline $...$, display $$...$$ on its own lines, units upright with a thin space: $12\\,\\mathrm{m\\,s^{-1}}$.
Do not emit raw Typst, shortcodes, executable code cells, or image file paths.
Do not wrap the answer in a code fence and do not add a title heading.
"""


@dataclass(frozen=True)
class Unit:
    title: str
    words: int
    role: str


def units_for(chapter: dict) -> list[Unit]:
    total = max(int(chapter["pages"]), 1) * WORDS_PER_PAGE
    subsections = chapter.get("subsections") or []
    if subsections:
        opener_words = max(160, int(total * 0.10))
        closing_words = max(200, int(total * 0.15))
        share = max(180, (total - opener_words - closing_words) // len(subsections))
        units = [
            Unit(
                "Chapter opener and dual-curriculum objectives",
                opener_words,
                "Open the chapter with a phenomenon, command verbs, and three deep questions.",
            )
        ]
        for subsection in subsections:
            units.append(
                Unit(
                    f"{subsection['number']} {subsection['title']}",
                    share,
                    "Teach this subsection with prose, two concrete examples, and the boxes that fit.",
                )
            )
        units.append(
            Unit(
                "End of chapter checkpoint, trap matrix, and tiered practice",
                closing_words,
                "Close with mistaken-error checks, an equation matrix, tiered problems, and a rubric.",
            )
        )
        return units
    share = max(180, total // len(MANDATORY_MODULES))
    return [Unit(title, share, title) for title in MANDATORY_MODULES]


def content_hash(book: dict, chapter: dict, units: list[Unit]) -> str:
    payload = {
        "version": PROMPT_VERSION,
        "book": book["id"],
        "curriculum": book.get("curriculum") or "",
        "chapter": chapter["number"],
        "title": chapter["title"],
        "pages": chapter["pages"],
        "units": [unit.title for unit in units],
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def curriculum_lock(book_id: str) -> str:
    if book_id.startswith("A"):
        return (
            "Align ONLY the Indonesian National Curriculum (KepKa BSKAP No. 046/H/KR/2025 Fase D/E) "
            "and Cambridge IGCSE Physics (0625/0972). Do not mention the IB Diploma Programme."
        )
    if book_id.startswith("B"):
        return (
            "Align ONLY the Indonesian National Curriculum (BSKAP 046/2025 Fase F) "
            "and Cambridge International AS & A Level Physics (9702). Do not mention the IB Diploma Programme."
        )
    return (
        "Align ONLY the Indonesian National Curriculum (BSKAP 046/2025 Fase F) "
        "and the IB Diploma Programme Physics 2025 syllabus. Do not mention Cambridge IGCSE or 9702."
    )


def system_prompt(book: dict) -> str:
    return "\n".join(
        [
            "You are a senior physics textbook author writing one section of a B5 student book.",
            curriculum_lock(book["id"]),
            f"Curriculum pairing: {book.get('curriculum') or 'see the chapter title.'}",
            BOX_GUIDE,
        ]
    )


def unit_prompt(book: dict, chapter: dict, unit: Unit) -> str:
    notes = chapter.get("notes") or ""
    return "\n".join(
        [
            f"Book: {book['code']} — {book['title']}",
            f"Chapter {chapter['number']}: {chapter['title']}",
            f"Chapter length target: {chapter['pages']} B5 pages.",
            f"Section: {unit.title}",
            f"Role: {unit.role}",
            f"Write about {unit.words} words for this section.",
            f"Syllabus note: {notes or 'none'}",
            "One paragraph carries one idea. Use SI units.",
        ]
    )


def complete_unit(gemini, system: str, user: str, target_words: int, expand: bool) -> str:
    text = gemini.generate(system=system, user=user)
    if expand and len(text.split()) < int(target_words * 0.55):
        more = gemini.generate(
            system=system,
            user=(
                f"The section is shorter than its {target_words}-word target. "
                "Continue in Quarto markdown without repeating the excerpt. "
                "Use ::: {.workspace}, ::: {.givens}, or ::: {.exam-trap} where they belong.\n\n"
                + text[-1500:]
            ),
        )
        text = text.rstrip() + "\n\n" + more.strip()
    return text


def assemble_chapter(chapter: dict, sections: list[tuple[str, str]]) -> str:
    parts = [f"# {chapter['title']}", ""]
    for title, body in sections:
        parts.append(f"## {title}")
        parts.append("")
        parts.append(body.strip())
        parts.append("")
    return sanitize_generated_qmd("\n".join(parts))
