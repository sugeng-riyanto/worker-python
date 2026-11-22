"""Colour palettes for the textbook layout, plus WCAG 2.x contrast checks.

One palette is a flat mapping of role -> hex colour. The Typst template, the
HTML/EPUB stylesheet, and reference.docx all read the same values, so every
format stays in the same colours. ``CONTRAST_RULES`` lists each foreground /
background pair the templates actually draw, with the WCAG AA minimum for it:
4.5:1 for normal text, 3:1 for large text (>= 14 pt bold) and for borders and
other non-text graphics. ``tests/test_palettes.py`` fails the build when any
pair falls short.
"""

from __future__ import annotations

DEFAULT_PALETTE = "studio"

# Role meanings (where the templates draw them):
#   paper         page / HTML background
#   ink           body text
#   heading       H1-H3 text on paper
#   muted         small grey text (running heads, metadata)
#   surface       white-ish box fill (worked example, practice, review)
#   primary       chapter band, section band, tabs, folio block (large text only)
#   primary-text  primary colour used as small text (H4, footer title, contents)
#   primary-soft  objectives / remember fill
#   on-primary    text on primary, accent, navy, blue, table-head fills
#   accent        worked-example border and tab
#   navy          practice tab, key terms, H5, caption labels, definition heads
#   blue          summary border/tab, links, info notes
#   table-head    table header row fill
#   *-soft        tinted box fills (dark text on top)
PALETTES: dict[str, dict[str, str]] = {
    "studio": {
        "paper": "#FFFFFF", "ink": "#1F2328", "heading": "#1F2328", "muted": "#5B6270", "surface": "#FFFFFF",
        "primary": "#E5670C", "primary-text": "#A84C08", "primary-soft": "#FDE6D2", "on-primary": "#FFFFFF",
        "accent": "#C8144A", "navy": "#1B4F8A", "blue": "#0072A3", "table-head": "#006F9E",
        "blue-soft": "#E1F1FA", "blue-softer": "#F1F8FC",
        "green": "#2E7533", "green-soft": "#E5F3E3", "purple": "#6E4594", "purple-soft": "#EFE6F6",
        "red": "#B91F1F", "red-soft": "#FCE7E6", "grey": "#5F6672", "grey-soft": "#F1F2F4",
    },
    "blue": {
        "paper": "#FFFFFF", "ink": "#1B2330", "heading": "#14223A", "muted": "#566070", "surface": "#FFFFFF",
        "primary": "#1C66C2", "primary-text": "#16509A", "primary-soft": "#DCE9FB", "on-primary": "#FFFFFF",
        "accent": "#C8144A", "navy": "#16386B", "blue": "#1A5FB4", "table-head": "#1A5FB4",
        "blue-soft": "#E3EEFC", "blue-softer": "#F3F7FD",
        "green": "#2E7533", "green-soft": "#E5F3E3", "purple": "#6E4594", "purple-soft": "#EFE6F6",
        "red": "#B91F1F", "red-soft": "#FCE7E6", "grey": "#5F6672", "grey-soft": "#F1F2F4",
    },
    "classic": {
        "paper": "#FFFFFF", "ink": "#1A1A1A", "heading": "#1A1A1A", "muted": "#5B6270", "surface": "#FFFFFF",
        "primary": "#0273B5", "primary-text": "#025F94", "primary-soft": "#D3E7F7", "on-primary": "#FFFFFF",
        "accent": "#02659F", "navy": "#1D3F66", "blue": "#0268A3", "table-head": "#0268A3",
        "blue-soft": "#D9E8F5", "blue-softer": "#EEF5FB",
        "green": "#2E7533", "green-soft": "#E4F1E8", "purple": "#6D4C9A", "purple-soft": "#ECE5F5",
        "red": "#B0281C", "red-soft": "#FBE9E7", "grey": "#5F6672", "grey-soft": "#EFEFEF",
    },
    "teal": {
        "paper": "#FFFFFF", "ink": "#17282A", "heading": "#0F3B3C", "muted": "#53625F", "surface": "#FFFFFF",
        "primary": "#0E8082", "primary-text": "#0A6466", "primary-soft": "#D6F1F0", "on-primary": "#FFFFFF",
        "accent": "#B83C0B", "navy": "#134E4A", "blue": "#0B6A84", "table-head": "#0B6A84",
        "blue-soft": "#DDF3F2", "blue-softer": "#F0FAF9",
        "green": "#2E7533", "green-soft": "#E5F3E3", "purple": "#6E4594", "purple-soft": "#EFE6F6",
        "red": "#B91F1F", "red-soft": "#FCE7E6", "grey": "#5F6672", "grey-soft": "#F1F2F4",
    },
    "forest": {
        "paper": "#FFFFFF", "ink": "#1B261D", "heading": "#173A22", "muted": "#56614F", "surface": "#FFFFFF",
        "primary": "#2E7D32", "primary-text": "#24622A", "primary-soft": "#DFF0DB", "on-primary": "#FFFFFF",
        "accent": "#A84B08", "navy": "#1B4332", "blue": "#2A6548", "table-head": "#2A6548",
        "blue-soft": "#E3F1E1", "blue-softer": "#F3F9F2",
        "green": "#2B6A30", "green-soft": "#E5F3E3", "purple": "#6E4594", "purple-soft": "#EFE6F6",
        "red": "#B91F1F", "red-soft": "#FCE7E6", "grey": "#5F6672", "grey-soft": "#F1F2F4",
    },
    "crimson": {
        "paper": "#FFFFFF", "ink": "#2A1A1E", "heading": "#4A1020", "muted": "#64565A", "surface": "#FFFFFF",
        "primary": "#B91C3C", "primary-text": "#991733", "primary-soft": "#F9DDE3", "on-primary": "#FFFFFF",
        "accent": "#1D4E89", "navy": "#4A1020", "blue": "#9F1239", "table-head": "#9F1239",
        "blue-soft": "#FBE7EB", "blue-softer": "#FDF4F6",
        "green": "#2E7533", "green-soft": "#E5F3E3", "purple": "#6E4594", "purple-soft": "#EFE6F6",
        "red": "#A61B1B", "red-soft": "#FCE7E6", "grey": "#5F6672", "grey-soft": "#F1F2F4",
    },
    "purple": {
        "paper": "#FFFFFF", "ink": "#211A2E", "heading": "#2E1A5C", "muted": "#5E5868", "surface": "#FFFFFF",
        "primary": "#6D3FB5", "primary-text": "#5A3396", "primary-soft": "#E8DEF8", "on-primary": "#FFFFFF",
        "accent": "#A51FB6", "navy": "#2E1A5C", "blue": "#5B3FA8", "table-head": "#5B3FA8",
        "blue-soft": "#ECE6FA", "blue-softer": "#F7F3FD",
        "green": "#2E7533", "green-soft": "#E5F3E3", "purple": "#6A3D99", "purple-soft": "#EFE6F6",
        "red": "#B91F1F", "red-soft": "#FCE7E6", "grey": "#5F6672", "grey-soft": "#F1F2F4",
    },
    "amber": {
        "paper": "#FFFFFF", "ink": "#2A2114", "heading": "#4A3005", "muted": "#625947", "surface": "#FFFFFF",
        "primary": "#B36A00", "primary-text": "#8A5200", "primary-soft": "#FCEBC9", "on-primary": "#FFFFFF",
        "accent": "#B4231A", "navy": "#5A3A06", "blue": "#8F5206", "table-head": "#8F5206",
        "blue-soft": "#FDF0D5", "blue-softer": "#FEF8EA",
        "green": "#2E7533", "green-soft": "#E5F3E3", "purple": "#6E4594", "purple-soft": "#EFE6F6",
        "red": "#B91F1F", "red-soft": "#FCE7E6", "grey": "#5F6672", "grey-soft": "#F1F2F4",
    },
    "dark": {
        "paper": "#121826", "ink": "#E6E9EF", "heading": "#F3F4F6", "muted": "#AEB6C4", "surface": "#1A2130",
        "primary": "#FB923C", "primary-text": "#FDBA74", "primary-soft": "#2A2118", "on-primary": "#111827",
        "accent": "#F472B6", "navy": "#93C5FD", "blue": "#38BDF8", "table-head": "#7DD3FC",
        "blue-soft": "#172338", "blue-softer": "#18202E",
        "green": "#4ADE80", "green-soft": "#15261C", "purple": "#C4B5FD", "purple-soft": "#221C33",
        "red": "#F87171", "red-soft": "#2C1A1C", "grey": "#9CA3AF", "grey-soft": "#1E2430",
    },
}

# Palettes meant for screens. DOCX (printed in Word) uses LIGHT_FALLBACK instead.
SCREEN_ONLY = {"dark"}
LIGHT_FALLBACK = "studio"
# Theme -> palette when no palette is chosen.
THEME_DEFAULT = {"studio": "studio", "classic": "classic"}

TEXT, LARGE, GRAPHIC = 4.5, 3.0, 3.0
_SOFTS = ("primary-soft", "blue-soft", "blue-softer", "green-soft", "purple-soft", "red-soft", "grey-soft", "surface")

# (foreground, background, minimum, where it is drawn)
CONTRAST_RULES: list[tuple[str, str, float, str]] = [
    ("ink", "paper", TEXT, "body text"),
    *[("ink", soft, TEXT, f"body text in {soft} boxes / table rows") for soft in _SOFTS],
    ("heading", "paper", TEXT, "H1-H3 titles on paper"),
    ("muted", "paper", TEXT, "running head, metadata"),
    ("primary-text", "paper", TEXT, "H4, footer chapter title, contents"),
    ("primary-text", "primary-soft", TEXT, "objectives / remember label"),
    ("primary-text", "blue-softer", TEXT, "hook box heading"),
    ("navy", "paper", TEXT, "key terms, H5, caption labels"),
    ("navy", "blue-soft", TEXT, "definition / key-terms heading"),
    ("navy", "surface", TEXT, "QR note heading"),
    ("blue", "paper", TEXT, "links"),
    ("blue", "blue-softer", TEXT, "info note heading"),
    ("green", "green-soft", TEXT, "workspace / quick-check heading"),
    ("red", "red-soft", TEXT, "exam-trap heading"),
    ("purple", "purple-soft", TEXT, "practical / enrichment heading"),
    ("grey", "grey-soft", TEXT, "teacher-note heading"),
    ("grey", "paper", TEXT, "figure-brief heading"),
    ("accent", "red-soft", TEXT, "link note heading"),
    ("on-primary", "table-head", TEXT, "table header text (8.8 pt bold)"),
    ("on-primary", "navy", TEXT, "practice tab / unnumbered section band"),
    ("on-primary", "primary", LARGE, "chapter + section bands, tabs, folio (>= 14 pt bold)"),
    ("on-primary", "accent", LARGE, "worked-example tab (14 pt bold)"),
    ("on-primary", "blue", LARGE, "summary tab (14 pt bold)"),
    ("on-primary", "purple", LARGE, "strategy chip IDEAL (14 pt bold)"),
    ("on-primary", "green", LARGE, "strategy chip TPS / POE (14 pt bold)"),
    ("navy", "blue-softer", TEXT, "GUESS / free-body scaffold heading"),
    ("blue", "blue-softer", TEXT, "CER / data-analysis scaffold heading"),
    ("primary-text", "primary-soft", TEXT, "estimate-check / real-world scaffold heading"),
    ("grey", "grey-soft", TEXT, "teacher verification heading, image placeholder hint"),
    ("ink", "grey-soft", TEXT, "image placeholder brief"),
    ("primary", "paper", GRAPHIC, "band edges, rules, bullets"),
    ("accent", "paper", GRAPHIC, "worked-example border"),
    ("blue", "paper", GRAPHIC, "summary / review border"),
    ("green", "paper", GRAPHIC, "workspace rule"),
    ("red", "paper", GRAPHIC, "exam-trap rule"),
    ("purple", "paper", GRAPHIC, "practical rule"),
    ("grey", "paper", GRAPHIC, "dashed figure frame, write lines"),
]


def _channel(value: int) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def contrast_table(name: str) -> list[tuple[str, str, float, float, str]]:
    """Rows of (fg role, bg role, ratio, minimum, usage) for one palette."""
    p = PALETTES[name]
    return [(fg, bg, round(contrast(p[fg], p[bg]), 2), need, usage) for fg, bg, need, usage in CONTRAST_RULES]


def failures(name: str) -> list[str]:
    return [f"{name}: {fg} on {bg} = {ratio:.2f} < {need} ({usage})" for fg, bg, ratio, need, usage in contrast_table(name) if ratio < need]


def resolve(name: str | None, theme: str = "studio") -> str:
    key = (name or "").strip().lower()
    if key in PALETTES:
        return key
    return THEME_DEFAULT.get(theme, DEFAULT_PALETTE)


def typst_dict(name: str) -> str:
    p = PALETTES[name]
    body = ",\n".join(f'  "{k}": rgb("{v}")' for k, v in p.items())
    return f"#let bc-palette-name = \"{name}\"\n#let bc-palette = (\n{body},\n)\n#let bc-dark = {'true' if name in SCREEN_ONLY else 'false'}\n"


def css_vars(name: str) -> str:
    p = PALETTES[name]
    lines = "\n".join(f"  --bc-{k}: {v};" for k, v in p.items())
    if name in SCREEN_ONLY:
        extra = (
            "  color-scheme: dark;\n  --bc-deep: #fff;\n"
            "  --bc-shadow: 0 1px 2px rgba(0, 0, 0, 0.5), 0 8px 18px -6px rgba(0, 0, 0, 0.65);\n"
            "  --bc-shadow-lift: 0 2px 4px rgba(0, 0, 0, 0.55), 0 14px 28px -10px rgba(0, 0, 0, 0.7);\n"
        )
    else:
        extra = "  color-scheme: light;\n"
    return f"/* palette: {name} (generated) */\n:root {{\n{lines}\n{extra}}}\n"


def docx_palette(name: str) -> dict[str, str]:
    """Hex colours without '#', light palette only (Word documents print)."""
    key = LIGHT_FALLBACK if name in SCREEN_ONLY else name
    return {k: v.lstrip("#").upper() for k, v in PALETTES[key].items()}
