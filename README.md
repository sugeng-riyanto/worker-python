# Physics Textbook Studio

Export worker and chapter generator for the B5 physics textbook series. An author pastes a table of contents, or points at a TOC Google Doc. The generator writes a Quarto chapter, and the worker renders five products from one upload: PDF, DOCX, HTML, EPUB, and a page-turning flipbook.

The original upload is still at `Physics_Studio_Python_Export_Worker.zip`. The runnable code lives in `physics_studio/`.

## Architecture

```text
Apps Script (existing UI)
    |  POST /jobs/PDF|DOCX|HTML|EPUB|FLIPBOOK|ALL   (zip of .qmd + assets)
    v
export worker  (python -m physics_studio)
    |  stages a safe Quarto book, renders, signs download links for 30 minutes
    v
PDF (Typst textbook template, ISO B5)    DOCX (B5 reference styles)
HTML / EPUB (textbook CSS)               flipbook (PDF pages, offline HTML)

generator  (python -m physics_studio.generator)
    pasted TOC or Google Doc  ->  JSON
    Gemini or DeepSeek, one call per subsection or module, continue on truncation
    render ALL  ->  Drive Book Xn/outputs/<format>/
    Google Sheet row, idempotent by content hash
```

The worker keeps the per-format API the current Apps Script already calls. `ALL` is additive: one zip, one job, five signed links. `flipbook/flipbook.qmd` is no longer required and is ignored; the flipbook is built from the PDF.

Jobs are stored under `JOB_ROOT` (default `/tmp/physics-studio-jobs`) so a restart can still explain an interrupted render. Download links are only valid on the instance that rendered them. Run Cloud Run with `--max-instances=1`.

## Layout

| Path | Role |
| --- | --- |
| `physics_studio/worker.py` | HTTP API |
| `physics_studio/staging.py` | Zip checks, assets, project YAML |
| `physics_studio/render.py` | Quarto, combined HTML, error capture |
| `physics_studio/assets/` | Typst textbook template, Lua filters, CSS |
| `physics_studio/flipbook.py` | PDF pages to a self-contained flipbook |
| `physics_studio/generator/` | TOC parser, Gemini and DeepSeek, Drive, Sheets |
| `fixtures/master_toc.txt` | Series A0–C2 table of contents |
| `fixtures/sample_chapter/` | Chapter with a figure and all three boxes |
| `Dockerfile` | Quarto 1.11.9, textbook fonts, Poppler |

## Textbook layout

The PDF follows a modern IGCSE student-book layout (see `docs/LAYOUT.md`): ISO B5 page with a 34 mm outer sidebar, a coloured chapter opener, chapter tabs and folio blocks, banded numbered section headings, blue-header tables, and coloured learning boxes. Two themes ship: `studio` (default, orange/blue, sans body) and `classic` (blue, serif body). Pick one with `bc-theme: classic` in the uploaded `_quarto.yml`, or set `PHYSICS_THEME` on the worker.

Authors write ordinary fenced divs. Raw ` ```{=typst} ` blocks stay rejected. An optional `title="..."` overrides the label. Labels follow `lang`: English by default (`lang: en` or no `lang`), Indonesian for `lang: id`.

| Class (aliases) | PDF rendering | Default label (id / en) |
| --- | --- | --- |
| `.objectives` (`.tujuan`, `.learning-outcomes`) | peach panel under the section banner | Dalam subbab ini, kamu akan mempelajari: / In this section, you will learn the following: |
| `.worked-example` (`.contoh-soal`), `.givens` | white box, crimson tab, numbered per chapter | Contoh Soal 2.1 / Worked Example 2.1 |
| `.practice` (`.latihan`) | navy tab, numbered | Ayo Berlatih 2.1 / Let's Practise 2.1 |
| `.review` (`.uji-kompetensi`) | full-width box, orange tab | Ayo Mengulang / Let's Review |
| `.summary` (`.rangkuman`) | blue tab | Ringkasan / Summary |
| `.definition`, `.key-equation` (`.rumus`) | light-blue centred statement | — |
| `.workspace`, `.think`, `.exam-trap`, `.hook`, `.practical`, `.figure-brief`, `.note` | tinted box with a coloured rule | Ruang Kerja Aktif, Pertanyaan Pemantik, Jebakan Ujian, Fenomena, Kegiatan Praktikum, Ilustrasi |
| `.quick-check`, `.remember`, `.key-terms`, `.qr`, `.teacher-note`, `.enrichment`, `.info`, `.link` | sidebar note in the outer margin (main column if longer than ~420 characters) | Cek Cepat, Ingat!, Istilah Kunci, Pindai, Catatan Guru, Pengayaan, Tahukah Kamu?, Tautan |

`textbook.lua` runs before the box filter. It turns Google Docs' escaped `\$...\$` back into math, strips `CHAPTER n:` / `MODULE n:` prefixes, title-cases all-caps headings, and recovers boxes from older drafts (scaffold headings such as "Sub-Section Pedagogical Header", and labelled blockquotes such as "QR WATCH" or "ACTIVE LEARNING WORKSPACE").

| Format | Rendering |
| --- | --- |
| PDF | `typst-show.typ` (`bc-box`, `bc-aside`), marginalia sidebar from Quarto's bundled packages |
| HTML and EPUB | `textbook.css`; sidebar notes float right and stack on phones; HTML embeds the fonts |
| DOCX | Calibri / Arial Narrow styles, orange heading bands, banded tables, one paragraph style per box |
| DOCX | Paragraph styles `GivensBox`, `WorkspaceBox`, `ExamTrap` in the B5 reference doc |

`_quarto.yml` in the zip is read for metadata only: title, subtitle, author, language, date, cover image, and EPUB publisher, rights, description, and identifier. Execution, filters, and output paths in that file are ignored. Missing metadata still defaults to the previous title and author; `lang` now defaults to `en` (English labels). Set `lang: id` for Indonesian labels.

Images (`.png`, `.jpg`, `.jpeg`, `.svg`) and `.css` are kept when the path stays inside the project. SVG script and CSS `@import` are rejected. Each format no longer needs its own upload.

## Local run

Python 3.11+, Quarto 1.11.9, and Poppler (`pdftoppm`). The Docker image already has them, plus Source Serif 4 and Inter.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# put a real QUARTO_WORKER_TOKEN in .env, then:
set -a && . ./.env && set +a
python -m physics_studio
```

The process listens on `0.0.0.0` and on `PORT` (Cloud Run), falling back to `QUARTO_WORKER_PORT` and then `8080`. Set `QUARTO_WORKER_BIND=127.0.0.1` to keep a local process on loopback.

```bash
python -m unittest discover -s tests
QUARTO_WORKER_TOKEN=... python scripts/verify_sample.py --out out/sample
```

Generator without credentials:

```bash
python -m physics_studio.generator \
  --toc-file fixtures/master_toc.txt \
  --book A0 --chapter 1 \
  --dry-run --out out/dry-run
```

That writes `toc.json` for every series, a chapter `.qmd` using the three boxes, placeholder files under `drive/Book A0/outputs/<format>/`, and one Sheet row in `sheet.json`. A second run with the same chapter returns the existing row and does not call the model again.

## Cloud Run

Build from this directory. The image compiles a tiny chapter during the build so the Typst template is known to compile. Fonts (Source Sans 3, Barlow Condensed, both SIL OFL) are installed into `/usr/local/share/fonts/textbook`; `PHYSICS_FONT_DIR` points elsewhere for local runs.

```bash
gcloud run deploy physics-studio-worker \
  --source . \
  --region asia-southeast2 \
  --memory 2Gi --cpu 2 \
  --timeout 900 \
  --concurrency 8 \
  --max-instances 1 \
  --no-cpu-throttling \
  --set-env-vars QUARTO_WORKER_TOKEN=...
```

`--no-cpu-throttling` matters: the HTTP call returns `202` immediately and Quarto keeps running on a background thread. Cloud Run throttles CPU after the response unless CPU is always allocated. `--max-instances=1` matters because job files live on the instance disk. Polls and downloads can share the instance (`--concurrency 8`); only one Quarto render runs at a time unless `MAX_RUNNING_JOBS` is raised.

`GET /healthz` is unauthenticated and returns `{"ok": true}`.

Finished jobs do not count toward the busy limit. A job is rejected with `429` only when queued plus running work has reached `MAX_RUNNING_JOBS + MAX_QUEUED_JOBS` (defaults 1 and 8). Finished jobs are kept until `JOB_TTL_SECONDS` (30 minutes) and then deleted. `MAX_RETAINED_JOBS` (default 40) drops the oldest finished job first if renders pile up faster than that.

## Apps Script contract

Script properties: `QUARTO_WORKER_URL` (origin only, no path) and `QUARTO_WORKER_TOKEN` (the same secret as the worker). Send the token in the `Authorization` header. Do not put it in the URL.

Zip the chapter at the archive root. `index.qmd` is optional. `_quarto.yml` is optional and is used only for the metadata fields above. Asset paths in the markdown must match paths in the zip, for example `images/vernier.png`.

### Enqueue

`POST /jobs/ALL` or `POST /jobs/PDF` (also `DOCX`, `HTML`, `EPUB`, `FLIPBOOK`).

```http
POST /jobs/ALL
Authorization: Bearer <QUARTO_WORKER_TOKEN>
Content-Type: application/zip

<zip bytes>
```

`202` response:

```json
{"job": "0123456789abcdef0123456789abcdef"}
```

Other responses: `401` `{"error": "Unauthorized"}`, `400` `{"error": "<safe reason>"}`, `413` `{"error": "Invalid archive size"}`, `429` `{"error": "Renderer busy"}`, `404` `{"error": "Unknown format"}`.

```javascript
function enqueueRender(blob) {
  const props = PropertiesService.getScriptProperties();
  const response = UrlFetchApp.fetch(props.getProperty('QUARTO_WORKER_URL') + '/jobs/ALL', {
    method: 'post',
    contentType: 'application/zip',
    headers: { Authorization: 'Bearer ' + props.getProperty('QUARTO_WORKER_TOKEN') },
    payload: blob.getBytes(),
    muteHttpExceptions: true
  });
  const body = JSON.parse(response.getContentText() || '{}');
  if (response.getResponseCode() !== 202) {
    throw new Error(body.error || ('Render rejected: ' + response.getResponseCode()));
  }
  return body.job;
}
```

A single-format post such as `/jobs/PDF` is unchanged: the same `202` body, and the later `path` field still points at that one file.

### Poll

`GET /jobs/<job>` with the same `Authorization` header.

While the render is in progress:

```json
{"state": "queued"}
```

```json
{"state": "running"}
```

Failure includes the Quarto stderr tail:

```json
{"state": "failed", "error": "PDF render failed.\n<quarto stderr>"}
```

Success for `ALL`:

```json
{
  "state": "done",
  "path": "/files/<job>/<expires>/<signature>/physics.pdf",
  "outputs": {
    "PDF": "/files/<job>/<expires>/<signature>/physics.pdf",
    "DOCX": "/files/<job>/<expires>/<signature>/physics.docx",
    "HTML": "/files/<job>/<expires>/<signature>/index.html",
    "EPUB": "/files/<job>/<expires>/<signature>/physics.epub",
    "FLIPBOOK": "/files/<job>/<expires>/<signature>/flipbook.html"
  }
}
```

A one-format job still sets `path`, and also sets `outputs` with that single entry. `path` for `ALL` is the PDF. Links are relative to `QUARTO_WORKER_URL`, expire after 30 minutes, and do not need the bearer token. `DOCX` and `EPUB` are sent as attachments. HTML is one self-contained book file. The flipbook is one HTML file with the PDF pages embedded as JPEG, so it opens offline.

```javascript
function pollRender(jobId) {
  const props = PropertiesService.getScriptProperties();
  const response = UrlFetchApp.fetch(props.getProperty('QUARTO_WORKER_URL') + '/jobs/' + jobId, {
    method: 'get',
    headers: { Authorization: 'Bearer ' + props.getProperty('QUARTO_WORKER_TOKEN') },
    muteHttpExceptions: true
  });
  const body = JSON.parse(response.getContentText() || '{}');
  if (response.getResponseCode() !== 200) {
    throw new Error(body.error || 'Unknown job');
  }
  return body;
}
```

Poll until `state` is `done` or `failed`. On `done`, open `QUARTO_WORKER_URL + body.path`, or each value in `body.outputs`.

## Generator

Real runs need one model key and a service account (`GOOGLE_SERVICE_ACCOUNT_JSON` or `GOOGLE_APPLICATION_CREDENTIALS`), plus `DRIVE_ROOT_FOLDER_ID` or `DRIVE_ROOT_FOLDER_NAME`, and `SHEET_ID`. Set `GEMINI_API_KEY` (sent as `x-goog-api-key`) or `DEEPSEEK_API_KEY` (sent as `Authorization: Bearer` to `https://api.deepseek.com/chat/completions`). `LLM_PROVIDERS=deepseek,gemini` is the fallback order; a provider with no key is skipped. `GEMINI_MODELS` and `DEEPSEEK_MODELS` are comma-separated model lists. The current DeepSeek ids are `deepseek-flash` and `deepseek-v4-pro`. `deepseek-chat` and `deepseek-reasoner` were retired on 2026-07-24 and are accepted as aliases of non-thinking and thinking `deepseek-flash`.

The Sheets tab records `job_id`, `content_hash`, `book`, `chapter`, `status`, `attempts`, `error`, `output_links`, and `updated_at`. A finished row with the same hash is returned as-is. A failed row is retried and `attempts` increases.

```bash
python -m physics_studio.generator \
  --toc-file fixtures/master_toc.txt \
  --book A0 --chapter 1 \
  --out out/chapter
```

`--toc-doc-id <google doc id>` reads a Docs file with the service account instead of a local TOC. `--toc-only` writes `toc.json` and stops. `--force` regenerates a chapter that already succeeded.

Series A chapters are generated once per numbered subsection, plus an opener and a closing module, so a 40-page chapter is not one truncated call. Series B and C chapters have no numbered subsections; they are generated once per mandatory module. Gemini continues when `finishReason` is `MAX_TOKENS` or `LENGTH`. DeepSeek continues when `finish_reason` is `length`. HTTP 429 and 5xx retry with backoff, honoring `Retry-After`, and a failed provider is followed by the next one in `LLM_PROVIDERS`. If the section is still far under its word budget, one expansion call is made. Dry-run skips expansion, both model providers, Drive, and Sheets.

```bash
python -m physics_studio.generator \
  --toc-file fixtures/master_toc.txt \
  --book A0 --chapter 1 \
  --providers deepseek --model deepseek-flash \
  --out out/chapter
```

Drive uploads go to `Book A0/outputs/pdf/`, `docx/`, `html/`, `epub/`, and `flipbook/`.
