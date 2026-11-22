"""DeepSeek client. The OpenAI-compatible API takes the key as a Bearer token.

Live model ids (November 2026) are ``deepseek-flash`` and ``deepseek-v4-pro``.
``deepseek-chat`` and ``deepseek-reasoner`` were retired on 2026-07-24; they are
accepted here as aliases of non-thinking and thinking ``deepseek-flash``.
"""

from __future__ import annotations

import json
import os
import time

from physics_studio.generator.gemini import RETRY_STATUSES, urllib_transport

CONTINUE_REASONS = {"length", "max_tokens"}
DEFAULT_BASE_URL = "https://api.deepseek.com"
# deepseek-chat was non-thinking V4-Flash; deepseek-reasoner was its thinking mode.
LEGACY_MODELS = {
    "deepseek-chat": ("deepseek-flash", "disabled"),
    "deepseek-reasoner": ("deepseek-flash", "enabled"),
}


class DeepSeekError(RuntimeError):
    """The DeepSeek request failed after retries."""


def models_from_env(env: dict[str, str] | None = None) -> list[str]:
    source = os.environ if env is None else env
    raw = source.get("DEEPSEEK_MODELS") or source.get("DEEPSEEK_MODEL") or "deepseek-flash"
    models = [item.strip() for item in raw.split(",") if item.strip()]
    if not models:
        raise DeepSeekError("Set DEEPSEEK_MODEL or DEEPSEEK_MODELS")
    return models


def resolve_model(name: str, thinking: str | None = None) -> tuple[str, str]:
    """Return the live model id and whether thinking is enabled or disabled."""
    legacy = LEGACY_MODELS.get(name.strip().lower())
    model, implied = legacy if legacy else (name.strip(), "disabled")
    mode = (thinking or implied).strip().lower()
    if mode not in {"enabled", "disabled"}:
        raise DeepSeekError("DEEPSEEK_THINKING must be enabled or disabled")
    return model, mode


def _extract(payload: dict) -> tuple[str, str]:
    choices = payload.get("choices") or []
    if not choices:
        message = (payload.get("error") or {}).get("message") or "DeepSeek returned no choices"
        raise DeepSeekError(str(message))
    choice = choices[0]
    message = choice.get("message") or {}
    text = message.get("content") or ""
    if not isinstance(text, str):
        text = str(text)
    reason = str(choice.get("finish_reason") or "stop").lower()
    if not text.strip() and reason not in CONTINUE_REASONS:
        raise DeepSeekError("DeepSeek returned an empty message")
    return text, reason


class DeepSeek:
    def __init__(
        self,
        api_key: str,
        models: list[str],
        transport=None,
        sleep=time.sleep,
        max_retries: int = 5,
        max_continuations: int = 4,
        max_output_tokens: int = 16384,
        base_url: str = DEFAULT_BASE_URL,
        thinking: str | None = None,
    ):
        if not api_key:
            raise DeepSeekError("DEEPSEEK_API_KEY is empty")
        self.api_key = api_key
        self.models = models
        self.transport = transport or urllib_transport
        self.sleep = sleep
        self.max_retries = max_retries
        self.max_continuations = max_continuations
        self.max_output_tokens = max_output_tokens
        self.base_url = base_url.rstrip("/")
        self.thinking = thinking

    def generate(self, *, system: str, user: str) -> str:
        errors: list[str] = []
        for model in self.models:
            try:
                return self._generate_with_model(model, system, user)
            except DeepSeekError as exc:
                errors.append(f"{model}: {exc}")
        raise DeepSeekError(" ; ".join(errors) or "DeepSeek request failed")

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
        live_model, thinking = resolve_model(model, self.thinking)
        url = f"{self.base_url}/chat/completions"
        if "key=" in url or f"Bearer {self.api_key}" in url:
            raise DeepSeekError("Refusing to put the API key in the URL")
        body = json.dumps(
            {
                "model": live_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.3,
                "max_tokens": self.max_output_tokens,
                "stream": False,
                "thinking": {"type": thinking},
            }
        ).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        delay = 1.0
        last_error = "DeepSeek request failed"
        for attempt in range(self.max_retries):
            status, response_headers, payload = self.transport(url, headers, body)
            if status == 200:
                try:
                    parsed = json.loads(payload.decode("utf-8"))
                except json.JSONDecodeError as exc:
                    raise DeepSeekError("DeepSeek returned invalid JSON") from exc
                return _extract(parsed)
            detail = payload.decode("utf-8", errors="replace")[:500]
            last_error = f"HTTP {status}: {detail}"
            if status not in RETRY_STATUSES or attempt == self.max_retries - 1:
                raise DeepSeekError(last_error)
            retry_after = response_headers.get("Retry-After") or response_headers.get("retry-after")
            if retry_after and str(retry_after).isdigit():
                self.sleep(min(int(retry_after), 60))
            else:
                self.sleep(delay)
                delay = min(delay * 2, 30)
        raise DeepSeekError(last_error)
