"""Gemini client. The API key travels in a header, never in the URL."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from urllib.parse import quote

RETRY_STATUSES = {429, 500, 502, 503, 504}
CONTINUE_REASONS = {"MAX_TOKENS", "LENGTH"}


class GeminiError(RuntimeError):
    """The model request failed after retries."""


def models_from_env(env: dict[str, str] | None = None) -> list[str]:
    source = os.environ if env is None else env
    raw = source.get("GEMINI_MODELS") or source.get("GEMINI_MODEL") or "gemini-2.5-flash"
    models = [item.strip() for item in raw.split(",") if item.strip()]
    if not models:
        raise GeminiError("Set GEMINI_MODEL or GEMINI_MODELS")
    return models


def _extract(payload: dict) -> tuple[str, str]:
    candidates = payload.get("candidates") or []
    if not candidates:
        feedback = payload.get("promptFeedback") or {}
        reason = feedback.get("blockReason") or "Gemini returned no candidates"
        raise GeminiError(str(reason))
    candidate = candidates[0]
    parts = ((candidate.get("content") or {}).get("parts")) or []
    texts: list[str] = []
    for part in parts:
        if not isinstance(part, dict) or part.get("thought"):
            continue
        if isinstance(part.get("text"), str):
            texts.append(part["text"])
    if not texts:
        raise GeminiError("Gemini returned an empty candidate")
    return "".join(texts), str(candidate.get("finishReason") or "STOP")


class Gemini:
    def __init__(
        self,
        api_key: str,
        models: list[str],
        transport,
        sleep=time.sleep,
        max_retries: int = 5,
        max_continuations: int = 4,
        max_output_tokens: int = 16384,
    ):
        if not api_key:
            raise GeminiError("GEMINI_API_KEY is empty")
        self.api_key = api_key
        self.models = models
        self.transport = transport
        self.sleep = sleep
        self.max_retries = max_retries
        self.max_continuations = max_continuations
        self.max_output_tokens = max_output_tokens

    def generate(self, *, system: str, user: str) -> str:
        errors: list[str] = []
        for model in self.models:
            try:
                return self._generate_with_model(model, system, user)
            except GeminiError as exc:
                errors.append(f"{model}: {exc}")
        raise GeminiError(" ; ".join(errors) or "Gemini request failed")

    def _generate_with_model(self, model: str, system: str, user: str) -> str:
        pieces: list[str] = []
        prompt = user
        for _ in range(self.max_continuations + 1):
            text, reason = self._complete(model, system, prompt)
            pieces.append(text)
            if reason not in CONTINUE_REASONS:
                return "".join(pieces).strip()
            prompt = (
                "Continue the Quarto markdown from the exact cutoff. "
                "Do not repeat earlier sentences. Do not wrap the answer in a code fence.\n\n"
                "CUTOFF:\n"
                + text[-1500:]
            )
        return "".join(pieces).strip()

    def _complete(self, model: str, system: str, user: str) -> tuple[str, str]:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{quote(model, safe='')}:generateContent"
        )
        if "key=" in url:
            raise GeminiError("Refusing to put the API key in the URL")
        body = json.dumps(
            {
                "system_instruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": self.max_output_tokens,
                },
            }
        ).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }
        delay = 1.0
        last_error = "Gemini request failed"
        for attempt in range(self.max_retries):
            status, response_headers, payload = self.transport(url, headers, body)
            if status == 200:
                try:
                    parsed = json.loads(payload.decode("utf-8"))
                except json.JSONDecodeError as exc:
                    raise GeminiError("Gemini returned invalid JSON") from exc
                return _extract(parsed)
            detail = payload.decode("utf-8", errors="replace")[:500]
            last_error = f"HTTP {status}: {detail}"
            if status not in RETRY_STATUSES or attempt == self.max_retries - 1:
                raise GeminiError(last_error)
            retry_after = response_headers.get("Retry-After") or response_headers.get("retry-after")
            if retry_after and str(retry_after).isdigit():
                self.sleep(min(int(retry_after), 60))
            else:
                self.sleep(delay)
                delay = min(delay * 2, 30)
        raise GeminiError(last_error)


def urllib_transport(url: str, headers: dict[str, str], body: bytes, timeout: int = 120):
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            header_map = {key: value for key, value in response.headers.items()}
            return response.status, header_map, response.read()
    except urllib.error.HTTPError as exc:
        header_map = {key: value for key, value in exc.headers.items()} if exc.headers else {}
        return exc.code, header_map, exc.read()
