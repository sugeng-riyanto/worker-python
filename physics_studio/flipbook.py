"""Build an offline page-turning book from rendered PDF pages."""

from __future__ import annotations

import base64
import html
import shutil
import subprocess
from pathlib import Path

from physics_studio.render_error import RenderError


def rasterize_pdf(pdf: Path, work: Path, *, dpi: int = 110, timeout: int = 240) -> list[bytes]:
    """Render each PDF page to a JPEG. Requires Poppler's ``pdftoppm``."""
    if shutil.which("pdftoppm") is None:
        raise RenderError("pdftoppm is not installed, so the flipbook cannot be built.")
    work.mkdir(parents=True, exist_ok=True)
    prefix = work / "page"
    proc = subprocess.run(
        [
            "pdftoppm",
            "-jpeg",
            "-r",
            str(dpi),
            "-jpegopt",
            "quality=82",
            str(pdf),
            str(prefix),
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RenderError(f"Could not rasterize PDF pages.\n{detail[-2000:]}")
    pages = sorted(work.glob("page-*.jpg"), key=lambda path: int(path.stem.split("-")[-1]))
    if not pages:
        raise RenderError("The PDF has no pages to turn.")
    return [path.read_bytes() for path in pages]


def flipbook_html(title: str, pages: list[bytes], *, lang: str = "id") -> str:
    """Self-contained HTML. Page images are embedded, so the file works offline."""
    if not pages:
        raise RenderError("The flipbook needs at least one page image.")
    encoded = [
        "data:image/jpeg;base64," + base64.b64encode(page).decode("ascii")
        for page in pages
    ]
    payload = ",".join('"' + item + '"' for item in encoded)
    safe_title = html.escape(title or "Physics Textbook", quote=True)
    safe_lang = html.escape(lang or "id", quote=True)
    count = len(pages)
    return f"""<!DOCTYPE html>
<html lang="{safe_lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_title}</title>
<style>
  :root {{
    --navy: #0F2942;
    --teal: #0284C7;
    --paper: #f7f4ee;
    --desk: #1b2430;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; height: 100%; }}
  body {{
    background: radial-gradient(circle at top, #24344a, var(--desk) 55%);
    color: white;
    font-family: Inter, "Segoe UI", sans-serif;
    display: flex;
    flex-direction: column;
    min-height: 100%;
  }}
  header {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: center;
    padding: 12px 18px;
  }}
  h1 {{
    margin: 0;
    font-size: 15px;
    font-weight: 650;
    letter-spacing: 0.01em;
  }}
  .controls {{ display: flex; gap: 8px; align-items: center; }}
  button {{
    background: var(--teal);
    color: white;
    border: 0;
    border-radius: 999px;
    padding: 8px 14px;
    font: inherit;
    font-weight: 700;
    cursor: pointer;
  }}
  button:disabled {{ opacity: 0.35; cursor: default; }}
  #indicator {{ min-width: 4.5rem; text-align: center; font-variant-numeric: tabular-nums; }}
  main {{
    flex: 1;
    display: grid;
    place-items: center;
    padding: 8px 16px 28px;
  }}
  #stage {{
    perspective: 2200px;
    width: min(92vw, 640px);
  }}
  #book {{
    position: relative;
    width: 100%;
    aspect-ratio: 176 / 250;
    transform-style: preserve-3d;
  }}
  #under, #sheet {{
    position: absolute;
    inset: 0;
  }}
  #under img, .face img {{
    width: 100%;
    height: 100%;
    object-fit: contain;
    background: var(--paper);
    border-radius: 2px 8px 8px 2px;
    box-shadow: 0 18px 40px rgba(0, 0, 0, 0.35);
  }}
  #sheet {{
    transform-origin: left center;
    transform-style: preserve-3d;
  }}
  .face {{
    position: absolute;
    inset: 0;
    backface-visibility: hidden;
    -webkit-backface-visibility: hidden;
  }}
  .face.back {{ transform: rotateY(180deg); }}
  #sheet.flip-forward {{ animation: flip-forward 0.72s ease forwards; }}
  #sheet.flip-back {{ animation: flip-back 0.72s ease forwards; }}
  @keyframes flip-forward {{
    from {{ transform: rotateY(0deg); }}
    to {{ transform: rotateY(-180deg); }}
  }}
  @keyframes flip-back {{
    from {{ transform: rotateY(-180deg); }}
    to {{ transform: rotateY(0deg); }}
  }}
  #hotspots {{
    position: absolute;
    inset: 0;
    display: grid;
    grid-template-columns: 1fr 1fr;
    z-index: 3;
  }}
  #hotspots button {{
    background: transparent;
    border-radius: 0;
    padding: 0;
    color: transparent;
  }}
  noscript p {{ color: white; padding: 1rem; }}
</style>
</head>
<body>
<header>
  <h1>{safe_title}</h1>
  <div class="controls">
    <button type="button" id="prev">Previous page</button>
    <span id="indicator">1 / {count}</span>
    <button type="button" id="next">Next page</button>
  </div>
</header>
<main>
  <div id="stage" data-page-count="{count}">
    <div id="book">
      <div id="under"><img id="under-img" alt=""></div>
      <div id="sheet">
        <div class="face front"><img id="front" alt="Page 1 of {count}"></div>
        <div class="face back"><img id="back" alt=""></div>
      </div>
      <div id="hotspots">
        <button type="button" id="zone-prev" aria-label="Previous page"></button>
        <button type="button" id="zone-next" aria-label="Next page"></button>
      </div>
    </div>
  </div>
</main>
<noscript><p>Page turning needs JavaScript. The rendered pages are embedded in this file.</p></noscript>
<script id="page-data" type="application/json">[{payload}]</script>
<script>
const pages = JSON.parse(document.getElementById("page-data").textContent);
const sheet = document.getElementById("sheet");
const front = document.getElementById("front");
const back = document.getElementById("back");
const under = document.getElementById("under-img");
const indicator = document.getElementById("indicator");
const prev = document.getElementById("prev");
const next = document.getElementById("next");
let index = 0;
let busy = false;

function paint(page) {{
  index = page;
  front.src = pages[page];
  front.alt = "Page " + (page + 1) + " of " + pages.length;
  const peek = Math.min(pages.length - 1, page + 1);
  under.src = pages[peek];
  indicator.textContent = (page + 1) + " / " + pages.length;
  prev.disabled = page === 0;
  next.disabled = page === pages.length - 1;
}}

function finish(className, page) {{
  sheet.addEventListener("animationend", function done() {{
    sheet.removeEventListener("animationend", done);
    sheet.classList.remove(className);
    paint(page);
    busy = false;
  }});
}}

function turn(delta) {{
  if (busy) return;
  const target = index + delta;
  if (target < 0 || target >= pages.length) return;
  busy = true;
  if (delta > 0) {{
    back.src = pages[target];
    back.alt = "Page " + (target + 1);
    sheet.classList.add("flip-forward");
    finish("flip-forward", target);
  }} else {{
    back.src = pages[index];
    front.src = pages[target];
    sheet.classList.add("flip-back");
    finish("flip-back", target);
  }}
}}

prev.addEventListener("click", () => turn(-1));
next.addEventListener("click", () => turn(1));
document.getElementById("zone-prev").addEventListener("click", () => turn(-1));
document.getElementById("zone-next").addEventListener("click", () => turn(1));
document.addEventListener("keydown", (event) => {{
  if (event.key === "ArrowRight" || event.key === "PageDown") turn(1);
  if (event.key === "ArrowLeft" || event.key === "PageUp") turn(-1);
}});
paint(0);
</script>
</body>
</html>
"""


def write_flipbook(pdf: Path, destination: Path, *, title: str, lang: str, timeout: int) -> None:
    pages = rasterize_pdf(pdf, destination.parent / "_pages", timeout=timeout)
    destination.write_text(flipbook_html(title, pages, lang=lang), encoding="utf-8")
