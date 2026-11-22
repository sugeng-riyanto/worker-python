"""Choose Gemini, DeepSeek, or both, and fall through when a provider fails."""

from __future__ import annotations

import os

from physics_studio.generator.deepseek import DeepSeek, models_from_env as deepseek_models
from physics_studio.generator.gemini import Gemini, models_from_env as gemini_models
from physics_studio.generator.gemini import urllib_transport


class LLMError(RuntimeError):
    """Every configured provider failed."""


class Fallback:
    """Try each client in order. The first one that returns text wins."""

    def __init__(self, clients: list):
        if not clients:
            raise LLMError("No language-model providers are configured")
        self.clients = clients

    def generate(self, *, system: str, user: str) -> str:
        errors: list[str] = []
        for client in self.clients:
            name = client.__class__.__name__
            try:
                return client.generate(system=system, user=user)
            except Exception as exc:
                errors.append(f"{name}: {exc}")
        raise LLMError(" ; ".join(errors))


def _selected_models(provider: str, order: list[str], model: str | None, configured: list[str]) -> list[str]:
    if not model:
        return configured
    if len(order) == 1 or model.lower().startswith(provider):
        return [item.strip() for item in model.split(",") if item.strip()]
    return configured


def provider_order(env: dict[str, str], requested: str | None = None) -> list[str]:
    raw = requested or env.get("LLM_PROVIDERS") or env.get("LLM_PROVIDER") or ""
    if raw.strip():
        names = [item.strip().lower() for item in raw.split(",") if item.strip()]
    else:
        names = []
        if env.get("GEMINI_API_KEY", "").strip():
            names.append("gemini")
        if env.get("DEEPSEEK_API_KEY", "").strip():
            names.append("deepseek")
        if not names:
            names = ["gemini", "deepseek"]
    unknown = [name for name in names if name not in {"gemini", "deepseek"}]
    if unknown:
        raise LLMError("Unknown provider: " + ", ".join(unknown))
    return names


def build_client(env: dict[str, str] | None = None, transport=None, providers: str | None = None, model: str | None = None):
    """Build the generator client from the environment.

    ``LLM_PROVIDERS`` is a comma-separated order, for example ``deepseek,gemini``.
    A provider with no API key is skipped. ``model`` replaces that provider's model list
    when only one provider is selected.
    """
    source = os.environ if env is None else env
    transport = transport or urllib_transport
    clients = []
    order = provider_order(source, providers)
    for name in order:
        if name == "gemini":
            key = source.get("GEMINI_API_KEY", "").strip()
            if not key:
                continue
            models = _selected_models(name, order, model, gemini_models(source))
            max_tokens = int(source.get("GEMINI_MAX_OUTPUT_TOKENS") or source.get("LLM_MAX_OUTPUT_TOKENS") or 16384)
            clients.append(Gemini(key, models, transport, max_output_tokens=max_tokens))
        else:
            key = source.get("DEEPSEEK_API_KEY", "").strip()
            if not key:
                continue
            models = _selected_models(name, order, model, deepseek_models(source))
            max_tokens = int(source.get("DEEPSEEK_MAX_OUTPUT_TOKENS") or source.get("LLM_MAX_OUTPUT_TOKENS") or 16384)
            base = source.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            thinking = source.get("DEEPSEEK_THINKING") or None
            clients.append(
                DeepSeek(
                    key,
                    models,
                    transport,
                    max_output_tokens=max_tokens,
                    base_url=base,
                    thinking=thinking,
                )
            )
    if not clients:
        raise LLMError("Set GEMINI_API_KEY or DEEPSEEK_API_KEY")
    if len(clients) == 1:
        return clients[0]
    return Fallback(clients)
