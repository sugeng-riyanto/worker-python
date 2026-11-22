"""Process configuration. Secrets come from the environment and nowhere else."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def bind_address(env: dict[str, str] | None = None) -> tuple[str, int]:
    """Cloud Run sets ``PORT`` and expects ``0.0.0.0``.

    ``QUARTO_WORKER_PORT`` still works for the existing local setup when ``PORT``
    is unset. ``PORT`` wins when both are set.
    """
    source = os.environ if env is None else env
    host = source.get("QUARTO_WORKER_BIND", "0.0.0.0") or "0.0.0.0"
    port_text = source.get("PORT") or source.get("QUARTO_WORKER_PORT") or "8080"
    return host, int(port_text)


def _int_env(name: str, default: int, env: dict[str, str]) -> int:
    raw = env.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class Config:
    token: str
    host: str
    port: int
    ttl_seconds: int = 1800
    max_zip_bytes: int = 24 * 1024 * 1024
    max_uncompressed_bytes: int = 48 * 1024 * 1024
    max_asset_bytes: int = 8 * 1024 * 1024
    max_qmd_bytes: int = 2 * 1024 * 1024
    max_files: int = 300
    max_running: int = 1
    max_queued: int = 8
    max_retained: int = 40
    render_timeout: int = 240
    job_root: Path = Path("/tmp/physics-studio-jobs")

    @staticmethod
    def from_env(env: dict[str, str] | None = None) -> Config:
        source = os.environ if env is None else env
        token = source.get("QUARTO_WORKER_TOKEN", "")
        if len(token) < 32:
            raise SystemExit("Set QUARTO_WORKER_TOKEN to a random value of at least 32 characters.")
        host, port = bind_address(source)
        return Config(
            token=token,
            host=host,
            port=port,
            ttl_seconds=_int_env("JOB_TTL_SECONDS", 1800, source),
            max_zip_bytes=_int_env("MAX_ZIP_BYTES", 24 * 1024 * 1024, source),
            max_uncompressed_bytes=_int_env("MAX_UNCOMPRESSED_BYTES", 48 * 1024 * 1024, source),
            max_asset_bytes=_int_env("MAX_ASSET_BYTES", 8 * 1024 * 1024, source),
            max_qmd_bytes=_int_env("MAX_QMD_BYTES", 2 * 1024 * 1024, source),
            max_files=_int_env("MAX_ARCHIVE_FILES", 300, source),
            max_running=max(1, _int_env("MAX_RUNNING_JOBS", 1, source)),
            max_queued=max(0, _int_env("MAX_QUEUED_JOBS", 8, source)),
            max_retained=max(1, _int_env("MAX_RETAINED_JOBS", 40, source)),
            render_timeout=max(30, _int_env("RENDER_TIMEOUT_SECONDS", 240, source)),
            job_root=Path(source.get("JOB_ROOT", "/tmp/physics-studio-jobs")),
        )
