import json
import unittest

from physics_studio.generator.deepseek import DeepSeek, DeepSeekError, resolve_model
from physics_studio.generator.llm import Fallback, LLMError, build_client


def _chat(reason: str, text: str) -> tuple[int, dict, bytes]:
    payload = {
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text, "reasoning_content": "hidden"},
                "finish_reason": reason,
            }
        ]
    }
    return 200, {}, json.dumps(payload).encode()


class DeepSeekTests(unittest.TestCase):
    def test_legacy_names_map_to_current_models(self):
        self.assertEqual(resolve_model("deepseek-chat"), ("deepseek-flash", "disabled"))
        self.assertEqual(resolve_model("deepseek-reasoner"), ("deepseek-flash", "enabled"))
        self.assertEqual(resolve_model("deepseek-v4-pro", "disabled"), ("deepseek-v4-pro", "disabled"))

    def test_bearer_key_and_length_continuation(self):
        seen = []
        replies = [
            (429, {"Retry-After": "0"}, b'{"error":{"message":"slow down"}}'),
            _chat("length", "Hello "),
            _chat("stop", "world"),
        ]

        def transport(url, headers, body):
            seen.append((url, headers, json.loads(body.decode())))
            return replies.pop(0)

        client = DeepSeek(
            "test-key",
            ["deepseek-chat"],
            transport,
            sleep=lambda _seconds: None,
            max_retries=4,
        )
        self.assertEqual(client.generate(system="system", user="write"), "Hello world")
        self.assertEqual(len(seen), 3)
        for url, headers, body in seen:
            self.assertEqual(url, "https://api.deepseek.com/chat/completions")
            self.assertNotIn("key=", url)
            self.assertNotIn("test-key", url)
            self.assertEqual(headers["Authorization"], "Bearer test-key")
            self.assertEqual(body["model"], "deepseek-flash")
            self.assertEqual(body["thinking"], {"type": "disabled"})
        self.assertIn("Hello ", seen[-1][2]["messages"][-1]["content"])

    def test_reasoner_alias_enables_thinking(self):
        seen = []

        def transport(url, headers, body):
            seen.append(json.loads(body.decode()))
            return _chat("stop", "done")

        DeepSeek("k", ["deepseek-reasoner"], transport, sleep=lambda _s: None).generate(system="s", user="u")
        self.assertEqual(seen[0]["thinking"], {"type": "enabled"})
        self.assertEqual(seen[0]["model"], "deepseek-flash")

    def test_does_not_retry_a_client_error_or_the_next_model_after_success(self):
        calls = []

        def transport(url, headers, body):
            calls.append(json.loads(body.decode())["model"])
            return 400, {}, b'{"error":{"message":"bad request"}}'

        client = DeepSeek("k", ["deepseek-flash", "deepseek-v4-pro"], transport, sleep=lambda _s: None, max_retries=4)
        with self.assertRaises(DeepSeekError):
            client.generate(system="s", user="u")
        self.assertEqual(calls, ["deepseek-flash", "deepseek-v4-pro"])


class FallbackTests(unittest.TestCase):
    def test_uses_the_next_provider_when_the_first_fails(self):
        class Down:
            def generate(self, *, system, user):
                raise DeepSeekError("quota")

        class Up:
            def generate(self, *, system, user):
                return "chapter"

        self.assertEqual(Fallback([Down(), Up()]).generate(system="s", user="u"), "chapter")
        with self.assertRaises(LLMError):
            Fallback([Down(), Down()]).generate(system="s", user="u")

    def test_provider_order_and_model_override_come_from_configuration(self):
        env = {
            "GEMINI_API_KEY": "gemini-secret",
            "DEEPSEEK_API_KEY": "deepseek-secret",
            "LLM_PROVIDERS": "deepseek,gemini",
            "DEEPSEEK_MODELS": "deepseek-flash,deepseek-v4-pro",
            "GEMINI_MODELS": "gemini-2.5-flash",
        }
        client = build_client(env, transport=lambda *args: None)
        self.assertIsInstance(client, Fallback)
        self.assertIsInstance(client.clients[0], DeepSeek)
        self.assertEqual(client.clients[0].models, ["deepseek-flash", "deepseek-v4-pro"])
        only = build_client(env, transport=lambda *args: None, providers="deepseek", model="deepseek-v4-pro")
        self.assertIsInstance(only, DeepSeek)
        self.assertEqual(only.models, ["deepseek-v4-pro"])
        self.assertEqual(only.base_url, "https://api.deepseek.com")
        with self.assertRaises(LLMError):
            build_client({}, transport=lambda *args: None)


if __name__ == "__main__":
    unittest.main()
