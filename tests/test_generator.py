import json
import tempfile
import unittest
import urllib.error
from io import StringIO
from contextlib import redirect_stdout
from pathlib import Path

from physics_studio.generator.cli import main
from physics_studio.generator.docs_text import document_plain_text
from physics_studio.generator.gemini import Gemini, GeminiError
from physics_studio.generator.mock import MockGemini
from physics_studio.generator.pipeline import GenerateRequest, run_job
from physics_studio.generator.qmd import complete_unit
from physics_studio.generator.renderers import DryRenderer
from physics_studio.generator.storage import LocalLibrary, LocalSheet
from physics_studio.safety import risky_markup


def _response(reason: str, text: str) -> tuple[int, dict, bytes]:
    payload = {
        "candidates": [
            {
                "content": {"role": "model", "parts": [{"text": text}, {"thought": True, "text": "hidden"}]},
                "finishReason": reason,
            }
        ]
    }
    return 200, {}, json.dumps(payload).encode()


class GeminiTests(unittest.TestCase):
    def test_retries_429_and_continues_after_truncation_without_putting_the_key_in_the_url(self):
        seen = []
        replies = [
            (429, {"Retry-After": "0"}, b'{"error":{"message":"slow down"}}'),
            _response("MAX_TOKENS", "Hello "),
            _response("STOP", "world"),
        ]

        def transport(url, headers, body):
            seen.append((url, headers))
            return replies.pop(0)

        client = Gemini("test-key", ["gemini-test"], transport, sleep=lambda _seconds: None, max_retries=4)
        self.assertEqual(client.generate(system="s", user="u"), "Hello world")
        self.assertTrue(all("key=" not in url for url, _headers in seen))
        self.assertTrue(all(headers["x-goog-api-key"] == "test-key" for _url, headers in seen))
        self.assertEqual(len(seen), 3)

    def test_does_not_retry_a_client_error(self):
        calls = []

        def transport(url, headers, body):
            calls.append(url)
            return 400, {}, b'{"error":{"message":"bad request"}}'

        client = Gemini("k", ["gemini-test"], transport, sleep=lambda _seconds: None, max_retries=4)
        with self.assertRaises(GeminiError):
            client.generate(system="s", user="u")
        self.assertEqual(len(calls), 1)


class DocsTests(unittest.TestCase):
    def test_reads_paragraphs_and_table_cells(self):
        text = document_plain_text(
            {
                "body": {
                    "content": [
                        {"paragraph": {"elements": [{"textRun": {"content": "Book A0\n"}}]}},
                        {
                            "table": {
                                "tableRows": [
                                    {"tableCells": [{"content": [{"paragraph": {"elements": [{"textRun": {"content": "1.1 Units\n"}}]}}]}]}
                                ]
                            }
                        },
                    ]
                }
            }
        )
        self.assertIn("Book A0", text)
        self.assertIn("1.1 Units", text)


class PipelineTests(unittest.TestCase):
    def _run(self, out: Path, gemini=None, chapter=1, book="A0"):
        toc = Path("fixtures/master_toc.txt").read_text(encoding="utf-8")
        return run_job(
            GenerateRequest(
                toc_text=toc,
                book=book,
                chapter=chapter,
                out_dir=out,
                expand=False,
                author="Sugeng Riyanto",
            ),
            gemini or MockGemini(),
            LocalLibrary(out / "drive"),
            LocalSheet(out / "sheet.json"),
            DryRenderer(),
        )

    def test_dry_run_is_idempotent_and_writes_boxes(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root))
        model = MockGemini()
        result = self._run(root, model)
        self.assertEqual(result["status"], "done")
        self.assertEqual(len(model.calls), 7)
        qmd = Path(result["qmd"]).read_text(encoding="utf-8")
        for kind in ("givens", "workspace", "exam-trap"):
            self.assertIn(f"{{.{kind}}}", qmd)
        self.assertFalse(risky_markup(qmd))
        toc = json.loads((root / "toc.json").read_text(encoding="utf-8"))
        self.assertEqual(len(toc["books"]), 6)
        self.assertTrue((root / "drive" / "Book A0" / "outputs" / "pdf").is_dir())
        self.assertTrue((root / "drive" / "Book A0" / "outputs" / "flipbook").is_dir())
        sheet = json.loads((root / "sheet.json").read_text(encoding="utf-8"))
        self.assertEqual(sheet[0]["status"], "done")
        self.assertEqual(sheet[0]["attempts"], 1)
        self.assertEqual(set(sheet[0]["output_links"]), {"pdf", "docx", "html", "epub", "flipbook"})
        again = self._run(root, model)
        self.assertTrue(again["idempotent"])
        self.assertEqual(len(model.calls), 7)
        self.assertEqual(json.loads((root / "sheet.json").read_text(encoding="utf-8"))[0]["attempts"], 1)

    def test_failure_is_recorded_and_retried(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root))

        class Flaky:
            def __init__(self):
                self.failed = False
                self.inner = MockGemini()

            def generate(self, *, system, user):
                if not self.failed:
                    self.failed = True
                    raise RuntimeError("model returned 503")
                return self.inner.generate(system=system, user=user)

        model = Flaky()
        with self.assertRaises(RuntimeError):
            self._run(root, model)
        failed = json.loads((root / "sheet.json").read_text(encoding="utf-8"))[0]
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["attempts"], 1)
        self.assertIn("503", failed["error"])
        result = self._run(root, model)
        self.assertEqual(result["status"], "done")
        self.assertEqual(result["attempts"], 2)

    def test_short_sections_are_expanded(self):
        class Short:
            def __init__(self):
                self.calls = 0

            def generate(self, *, system, user):
                self.calls += 1
                return "Too short." if self.calls == 1 else ("word " * 40)

        model = Short()
        text = complete_unit(model, "system", "user", 40, expand=True)
        self.assertEqual(model.calls, 2)
        self.assertIn("word", text)

    def test_cli_dry_run(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root))
        buffer = StringIO()
        with redirect_stdout(buffer):
            code = main(
                [
                    "--toc-file",
                    "fixtures/master_toc.txt",
                    "--book",
                    "B1",
                    "--chapter",
                    "1",
                    "--dry-run",
                    "--out",
                    str(root),
                ]
            )
        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["status"], "done")
        self.assertIn("dry-run://Book B1/outputs/pdf/", next(iter(payload["outputs"].values())))


if __name__ == "__main__":
    unittest.main()
