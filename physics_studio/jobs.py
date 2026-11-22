"""Disk-backed job records. Finished jobs do not consume render capacity."""

from __future__ import annotations

import json
import shutil
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from physics_studio.config import Config


class BusyError(RuntimeError):
    """The render queue is full. Finished jobs are not counted."""


@dataclass
class Job:
    id: str
    state: str
    formats: list[str]
    primary: str
    created: float
    expires: float
    error: str = ""
    outputs: dict[str, str] = field(default_factory=dict)

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "state": self.state,
            "formats": self.formats,
            "primary": self.primary,
            "created": self.created,
            "expires": self.expires,
            "error": self.error,
            "outputs": self.outputs,
        }

    @staticmethod
    def from_json(payload: dict) -> Job:
        return Job(
            id=payload["id"],
            state=payload["state"],
            formats=list(payload["formats"]),
            primary=payload["primary"],
            created=float(payload["created"]),
            expires=float(payload["expires"]),
            error=payload.get("error") or "",
            outputs=dict(payload.get("outputs") or {}),
        )


class JobStore:
    def __init__(self, config: Config):
        self.config = config
        self.root = config.job_root
        self.root.mkdir(parents=True, exist_ok=True)
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()
        self._reload()

    def src_dir(self, job_id: str) -> Path:
        return self.root / job_id / "src"

    def output_dir(self, job_id: str) -> Path:
        return self.root / job_id / "output"

    def begin(self, formats: list[str], primary: str) -> Job:
        with self.lock:
            self._prune_locked()
            if self._active_locked() >= self.config.max_running + self.config.max_queued:
                raise BusyError("Renderer busy")
            now = time.time()
            job = Job(
                id=uuid.uuid4().hex,
                state="queued",
                formats=list(formats),
                primary=primary,
                created=now,
                expires=now + self.config.ttl_seconds,
            )
            self.jobs[job.id] = job
            self.src_dir(job.id).mkdir(parents=True, exist_ok=True)
            self._write_locked(job)
            return job

    def discard(self, job_id: str) -> None:
        with self.lock:
            self.jobs.pop(job_id, None)
            shutil.rmtree(self.root / job_id, ignore_errors=True)

    def update(self, job_id: str, **changes) -> Job:
        with self.lock:
            job = self.jobs[job_id]
            for key, value in changes.items():
                setattr(job, key, value)
            self._write_locked(job)
            return job

    def get(self, job_id: str) -> Job | None:
        with self.lock:
            self._prune_locked()
            job = self.jobs.get(job_id)
            return None if job is None else Job(**{**job.to_json(), "formats": list(job.formats), "outputs": dict(job.outputs)})

    def active_count(self) -> int:
        with self.lock:
            return self._active_locked()

    def _active_locked(self) -> int:
        return sum(job.state in {"queued", "running"} for job in self.jobs.values())

    def _prune_locked(self) -> None:
        now = time.time()
        for job in list(self.jobs.values()):
            if job.state in {"done", "failed"} and job.expires <= now:
                self._drop_locked(job.id)
        finished = [job for job in self.jobs.values() if job.state in {"done", "failed"}]
        finished.sort(key=lambda job: job.created)
        overflow = len(finished) - self.config.max_retained
        for job in finished[: max(0, overflow)]:
            self._drop_locked(job.id)

    def _drop_locked(self, job_id: str) -> None:
        self.jobs.pop(job_id, None)
        shutil.rmtree(self.root / job_id, ignore_errors=True)

    def _write_locked(self, job: Job) -> None:
        path = self.root / job.id / "status.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(job.to_json()), encoding="utf-8")
        temporary.replace(path)

    def _reload(self) -> None:
        for path in self.root.glob("*/status.json"):
            try:
                job = Job.from_json(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError, KeyError, TypeError):
                continue
            if job.state in {"queued", "running"}:
                job.state = "failed"
                job.error = "Render interrupted by process restart."
                job.expires = time.time() + self.config.ttl_seconds
            self.jobs[job.id] = job
            self._write_locked(job)
