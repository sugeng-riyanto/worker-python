"""Expiring download links. The token never appears in the URL."""

from __future__ import annotations

import hashlib
import hmac


def signature(token: str, job: str, filename: str, expires: int) -> str:
    message = f"{job}/{filename}/{int(expires)}".encode()
    return hmac.new(token.encode(), message, hashlib.sha256).hexdigest()


def signed_path(token: str, job: str, filename: str, expires: int) -> str:
    digest = signature(token, job, filename, expires)
    return f"/files/{job}/{int(expires)}/{digest}/{filename}"


def authorized(header: str, token: str) -> bool:
    expected = "Bearer " + token
    if len(header) != len(expected):
        return False
    return hmac.compare_digest(header, expected)
