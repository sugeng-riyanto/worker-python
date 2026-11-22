"""HTTP render worker.

``POST /jobs/{PDF|DOCX|HTML|EPUB|FLIPBOOK}`` keeps the Apps Script contract.
``POST /jobs/ALL`` renders every format from a single upload.
"""

from __future__ import annotations

import json
import logging
import mimetypes
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from zipfile import BadZipFile

from physics_studio.config import Config
from physics_studio.formats import parse_format
from physics_studio.jobs import BusyError, JobStore
from physics_studio.render import render_formats
from physics_studio.render_error import RenderError
from physics_studio.signing import authorized, signature, signed_path
from physics_studio.staging import Limits, StagingError, stage_zip

log = logging.getLogger("physics_studio.worker")

_JOB_PATH = re.compile(r"/jobs/([a-f0-9]{32})\Z")
_FILE_PATH = re.compile(r"/files/([a-f0-9]{32})/(\d{1,12})/([a-f0-9]{64})/([A-Za-z0-9._-]+)\Z")
_POST_PATH = re.compile(r"/jobs/(PDF|DOCX|HTML|EPUB|FLIPBOOK|ALL)\Z", re.IGNORECASE)


class App:
    def __init__(self, config: Config):
        self.config = config
        self.store = JobStore(config)
        self.pool = ThreadPoolExecutor(max_workers=config.max_running, thread_name_prefix="render")

    def limits(self) -> Limits:
        config = self.config
        return Limits(
            max_zip_bytes=config.max_zip_bytes,
            max_uncompressed_bytes=config.max_uncompressed_bytes,
            max_asset_bytes=config.max_asset_bytes,
            max_qmd_bytes=config.max_qmd_bytes,
            max_files=config.max_files,
        )

    def submit(self, raw: bytes, format_name: str) -> str:
        formats = parse_format(format_name)
        primary = "PDF" if format_name.upper() == "ALL" else formats[0]
        job = self.store.begin(formats, primary)
        try:
            stage_zip(raw, self.store.src_dir(job.id), self.limits())
        except (StagingError, BadZipFile, OSError) as exc:
            self.store.discard(job.id)
            if isinstance(exc, StagingError):
                raise
            raise StagingError("Invalid Quarto archive") from exc
        self.pool.submit(self._execute, job.id, formats)
        return job.id

    def _execute(self, job_id: str, formats: list[str]) -> None:
        self.store.update(job_id, state="running")
        try:
            outputs = render_formats(self.store.src_dir(job_id), formats, self.config.render_timeout)
            # Keep rendered files next to the status record the restart path reloads.
            output_dir = self.store.output_dir(job_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            source_dir = self.store.src_dir(job_id) / "_output"
            for filename in outputs.values():
                target = output_dir / filename
                target.write_bytes((source_dir / filename).read_bytes())
            self.store.update(
                job_id,
                state="done",
                outputs=outputs,
                error="",
                expires=time.time() + self.config.ttl_seconds,
            )
        except Exception as exc:
            message = str(exc).strip() or exc.__class__.__name__
            if not isinstance(exc, RenderError):
                message = f"Render failed: {message}"
            log.error("job %s failed: %s", job_id, message.splitlines()[0][:300])
            self.store.update(
                job_id,
                state="failed",
                error=message[:4000],
                expires=time.time() + self.config.ttl_seconds,
            )


def _json(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    if handler.close_connection:
        handler.send_header("Connection", "close")
    handler.end_headers()
    handler.wfile.write(body)


def _job_payload(app: App, job_id: str, job) -> dict:
    payload: dict = {"state": job.state}
    if job.error:
        payload["error"] = job.error
    if job.state == "done":
        outputs = {
            fmt: signed_path(app.config.token, job_id, filename, int(job.expires))
            for fmt, filename in job.outputs.items()
        }
        payload["outputs"] = outputs
        if job.primary in outputs:
            payload["path"] = outputs[job.primary]
        elif outputs:
            payload["path"] = next(iter(outputs.values()))
    return payload


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args) -> None:
            return

        def do_GET(self) -> None:  # noqa: N802
            try:
                self._get()
            except Exception:
                log.exception("GET failed")
                _json(self, 500, {"error": "Internal error"})

        def do_POST(self) -> None:  # noqa: N802
            self._body_consumed = False
            try:
                self._post()
            except Exception:
                log.exception("POST failed")
                self._discard_unread_body()
                _json(self, 500, {"error": "Internal error"})

        def _discard_unread_body(self) -> None:
            """Align a keep-alive connection before an early error response.

            A reverse proxy reuses the socket. If the declared body is still
            sitting in it, the next request line is parsed from those bytes and
            comes back 501. Bodies within the zip cap are discarded. Anything
            larger, chunked, or unreadable closes the connection instead of
            being buffered.
            """
            if self._body_consumed:
                return
            self._body_consumed = True
            encoding = self.headers.get("Transfer-Encoding", "")
            if encoding and encoding.lower() != "identity":
                self.close_connection = True
                return
            raw_length = self.headers.get("Content-Length")
            try:
                size = int(raw_length) if raw_length not in (None, "") else 0
            except ValueError:
                self.close_connection = True
                return
            if size < 0 or size > app.config.max_zip_bytes:
                self.close_connection = True
                return
            remaining = size
            try:
                while remaining:
                    chunk = self.rfile.read(min(remaining, 65536))
                    if not chunk:
                        self.close_connection = True
                        return
                    remaining -= len(chunk)
            except OSError:
                self.close_connection = True

        def _post(self) -> None:
            path = urlsplit(self.path).path
            if not authorized(self.headers.get("Authorization", ""), app.config.token):
                self._discard_unread_body()
                return _json(self, 401, {"error": "Unauthorized"})
            match = _POST_PATH.fullmatch(path)
            if not match:
                self._discard_unread_body()
                return _json(self, 404, {"error": "Unknown format"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                size = 0
            if size <= 0 or size > app.config.max_zip_bytes:
                self._discard_unread_body()
                return _json(self, 413, {"error": "Invalid archive size"})
            raw = self.rfile.read(size)
            self._body_consumed = True
            try:
                job_id = app.submit(raw, match.group(1))
            except BusyError:
                return _json(self, 429, {"error": "Renderer busy"})
            except StagingError as exc:
                return _json(self, 400, {"error": str(exc)})
            return _json(self, 202, {"job": job_id})

        def _get(self) -> None:
            path = urlsplit(self.path).path
            if path == "/healthz":
                return _json(self, 200, {"ok": True})
            match = _JOB_PATH.fullmatch(path)
            if match:
                if not authorized(self.headers.get("Authorization", ""), app.config.token):
                    return _json(self, 401, {"error": "Unauthorized"})
                job = app.store.get(match.group(1))
                if job is None:
                    return _json(self, 404, {"error": "Unknown job"})
                return _json(self, 200, _job_payload(app, match.group(1), job))
            link = _FILE_PATH.fullmatch(path)
            if not link:
                return _json(self, 404, {"error": "Unknown path"})
            job_id, expires_text, digest, filename = link.groups()
            expires = int(expires_text)
            if expires < time.time():
                return _json(self, 404, {"error": "Invalid or expired link"})
            job = app.store.get(job_id)
            allowed = set(job.outputs.values()) if job and job.state == "done" else set()
            expected = signature(app.config.token, job_id, filename, expires)
            if (
                job is None
                or filename not in allowed
                or not hmac_equal(digest, expected)
            ):
                return _json(self, 404, {"error": "Invalid or expired link"})
            target = (app.store.output_dir(job_id) / filename).resolve()
            root = app.store.output_dir(job_id).resolve()
            if not target.is_relative_to(root) or not target.is_file():
                return _json(self, 404, {"error": "File unavailable"})
            payload = target.read_bytes()
            content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "private, no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            if target.suffix in {".docx", ".epub"}:
                self.send_header("Content-Disposition", f'attachment; filename="{target.name}"')
            self.end_headers()
            self.wfile.write(payload)

    return Handler


def hmac_equal(left: str, right: str) -> bool:
    import hmac

    if len(left) != len(right):
        return False
    return hmac.compare_digest(left, right)


def serve(config: Config) -> ThreadingHTTPServer:
    app = App(config)
    httpd = ThreadingHTTPServer((config.host, config.port), make_handler(app))
    httpd.daemon_threads = True
    httpd.app = app  # type: ignore[attr-defined]
    return httpd


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = Config.from_env()
    httpd = serve(config)
    log.info("listening on %s:%s", config.host, config.port)
    thread = threading.Thread(target=httpd.serve_forever, name="http", daemon=True)
    thread.start()
    try:
        thread.join()
    except KeyboardInterrupt:
        httpd.shutdown()
