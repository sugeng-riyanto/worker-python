import http.client
import json
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from physics_studio.config import Config, bind_address
from physics_studio.formats import FILENAMES
from physics_studio.jobs import BusyError, JobStore
from physics_studio.render import render_env
from physics_studio.render_error import RenderError
from physics_studio.worker import serve
from tests.support import CHAPTER, png_bytes, zip_bytes

TOKEN = "unit-test-token-with-32-characters"


def _config(root: Path, **overrides) -> Config:
    values = dict(
        token=TOKEN,
        host="127.0.0.1",
        port=0,
        job_root=root,
        max_running=1,
        max_queued=0,
        max_retained=5,
        ttl_seconds=1800,
        render_timeout=30,
    )
    values.update(overrides)
    return Config(**values)


class ConfigTests(unittest.TestCase):
    def test_port_and_bind_defaults_suit_cloud_run(self):
        self.assertEqual(bind_address({}), ("0.0.0.0", 8080))
        self.assertEqual(bind_address({"QUARTO_WORKER_PORT": "8765"}), ("0.0.0.0", 8765))
        self.assertEqual(bind_address({"PORT": "9090", "QUARTO_WORKER_PORT": "8765"}), ("0.0.0.0", 9090))
        self.assertEqual(bind_address({"QUARTO_WORKER_BIND": "127.0.0.1", "PORT": "8080"}), ("127.0.0.1", 8080))

    def test_render_env_drops_secrets(self):
        env = render_env(
            {
                "PATH": "/usr/bin",
                "HOME": "/root",
                "QUARTO_WORKER_TOKEN": "secret",
                "GEMINI_API_KEY": "secret",
                "GOOGLE_SERVICE_ACCOUNT_JSON": "{}",
            }
        )
        self.assertNotIn("QUARTO_WORKER_TOKEN", env)
        self.assertNotIn("GEMINI_API_KEY", env)
        self.assertNotIn("GOOGLE_SERVICE_ACCOUNT_JSON", env)
        self.assertEqual(env["PATH"], "/usr/bin")


class CapacityTests(unittest.TestCase):
    def test_finished_jobs_do_not_consume_capacity(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        store = JobStore(_config(Path(root.name), max_running=1, max_queued=0, max_retained=20))
        first = store.begin(["PDF"], "PDF")
        store.update(first.id, state="done", outputs={"PDF": "physics.pdf"})
        for _ in range(8):
            done = store.begin(["PDF"], "PDF")
            store.update(done.id, state="done", outputs={"PDF": "physics.pdf"})
        extra = store.begin(["PDF"], "PDF")
        self.assertEqual(extra.state, "queued")
        store.update(extra.id, state="running")
        with self.assertRaises(BusyError):
            store.begin(["PDF"], "PDF")


class WorkerHttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.original = __import__("physics_studio.worker", fromlist=["render_formats"]).render_formats
        self.server = serve(_config(Path(self.tmp.name)))
        self.addCleanup(self._stop)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def _stop(self):
        import physics_studio.worker as worker

        self.server.shutdown()
        self.server.server_close()
        self.server.app.pool.shutdown(wait=True, cancel_futures=True)
        worker.render_formats = self.original

    def request(self, method, path, body=None, token=TOKEN):
        headers = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if body is not None:
            headers["Content-Length"] = str(len(body))
        req = urllib.request.Request(self.base + path, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status, response.read(), dict(response.headers)
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(), dict(exc.headers)

    def test_all_mode_returns_every_format_and_surfaces_errors(self):
        import physics_studio.worker as worker

        def fake(project, formats, timeout):
            out = project / "_output"
            out.mkdir(parents=True, exist_ok=True)
            produced = {}
            for fmt in formats:
                name = FILENAMES[fmt]
                (out / name).write_bytes(f"bytes-{fmt}".encode())
                produced[fmt] = name
            return produced

        worker.render_formats = fake
        archive = zip_bytes({"bab-01.qmd": CHAPTER, "images/vernier.png": png_bytes()})
        status, body, _ = self.request("POST", "/jobs/ALL", archive)
        self.assertEqual(status, 202, body)
        job = json.loads(body)["job"]
        state = {}
        for _ in range(50):
            status, body, _ = self.request("GET", f"/jobs/{job}")
            state = json.loads(body)
            if state["state"] in {"done", "failed"}:
                break
        self.assertEqual(state["state"], "done", state)
        self.assertEqual(set(state["outputs"]), {"PDF", "DOCX", "HTML", "EPUB", "FLIPBOOK"})
        self.assertTrue(state["path"].endswith("/physics.pdf"))
        status, downloaded, headers = self.request("GET", state["outputs"]["DOCX"], token=None)
        self.assertEqual(status, 200)
        self.assertEqual(downloaded, b"bytes-DOCX")
        self.assertIn("attachment", headers.get("Content-Disposition", ""))
        status, _, _ = self.request("GET", "/healthz", token=None)
        self.assertEqual(status, 200)

        def explode(project, formats, timeout):
            raise RenderError("typst: file not found: images/vernier.png")

        worker.render_formats = explode
        status, body, _ = self.request("POST", "/jobs/PDF", archive)
        failed = json.loads(body)["job"]
        error = {}
        for _ in range(50):
            _, body, _ = self.request("GET", f"/jobs/{failed}")
            error = json.loads(body)
            if error["state"] in {"done", "failed"}:
                break
        self.assertEqual(error["state"], "failed")
        self.assertIn("vernier.png", error["error"])

    def test_auth_and_single_format_contract(self):
        import physics_studio.worker as worker

        worker.render_formats = lambda project, formats, timeout: (_ for _ in ()).throw(AssertionError("no"))
        status, _, _ = self.request("POST", "/jobs/PDF", zip_bytes({"bab-01.qmd": "# A\n"}), token="nope")
        self.assertEqual(status, 401)
        status, _, _ = self.request("POST", "/jobs/SLIDES", b"zip", token=TOKEN)
        self.assertEqual(status, 404)
        status, body, _ = self.request("POST", "/jobs/PDF", zip_bytes({"bab-01.qmd": "```{=typst}\n#x\n```\n"}))
        self.assertEqual(status, 400)
        self.assertIn("Active source", json.loads(body)["error"])

    def test_unauthorized_body_does_not_poison_keepalive(self):
        import physics_studio.worker as worker

        worker.render_formats = self._write_pdf
        port = self.server.server_address[1]
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        self.addCleanup(conn.close)
        conn.request("POST", "/jobs/ALL", body=b"PK\x03\x04 leftover body")
        rejected = conn.getresponse()
        self.assertEqual(rejected.status, 401)
        self.assertNotEqual(rejected.getheader("Connection"), "close")
        rejected.read()
        reused = conn.sock
        archive = zip_bytes({"bab-01.qmd": "# Keepalive\n\nA unit.\n"})
        conn.request(
            "POST",
            "/jobs/ALL",
            body=archive,
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        self.assertIs(conn.sock, reused)
        accepted = conn.getresponse()
        payload = accepted.read()
        self.assertEqual(accepted.status, 202, payload)
        self.assertIn("job", json.loads(payload))

    def test_finished_job_does_not_cause_429(self):
        import physics_studio.worker as worker

        worker.render_formats = self._write_pdf
        archive = zip_bytes({"bab-01.qmd": "# Forces\n\nA force.\n"})
        first = self._wait_done(archive)
        self.assertEqual(first["state"], "done")
        status, _, _ = self.request("POST", "/jobs/PDF", archive)
        self.assertEqual(status, 202)

    def _write_pdf(self, project, formats, timeout):
        out = project / "_output"
        out.mkdir(parents=True, exist_ok=True)
        produced = {}
        for fmt in formats:
            (out / FILENAMES[fmt]).write_bytes(b"%PDF")
            produced[fmt] = FILENAMES[fmt]
        return produced

    def _wait_done(self, archive):
        status, body, _ = self.request("POST", "/jobs/PDF", archive)
        self.assertEqual(status, 202, body)
        job = json.loads(body)["job"]
        state = {}
        for _ in range(50):
            _, body, _ = self.request("GET", f"/jobs/{job}")
            state = json.loads(body)
            if state["state"] in {"done", "failed"}:
                return state
        return state


class ReferenceTests(unittest.TestCase):
    def test_b5_geometry_and_box_styles(self):
        from physics_studio.reference_docx import apply_b5

        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(root))
        path = root / "reference.docx"
        _minimal_docx(path)
        apply_b5(path)
        import zipfile

        with zipfile.ZipFile(path) as archive:
            document = archive.read("word/document.xml").decode("utf-8")
            styles = archive.read("word/styles.xml").decode("utf-8")
            settings = archive.read("word/settings.xml").decode("utf-8")
        self.assertIn('w:w="9978"', document)
        self.assertIn('w:h="14173"', document)
        self.assertIn("<w:mirrorMargins", settings)
        for style in ("WorkspaceBox", "GivensBox", "ExamTrap"):
            self.assertIn(style, styles)


def _minimal_docx(path: Path) -> None:
    import zipfile

    document = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>Hi</w:t></w:r></w:p>
  <w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>
  </w:body></w:document>"""
    styles = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/></w:style></w:styles>"""
    settings = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"></w:settings>"""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("word/document.xml", document)
        archive.writestr("word/styles.xml", styles)
        archive.writestr("word/settings.xml", settings)


if __name__ == "__main__":
    unittest.main()
