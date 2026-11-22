"""Shared fixtures for the export worker tests."""

from __future__ import annotations

import io
import struct
import zipfile
import zlib


def png_bytes(width: int = 2, height: int = 2, rgb: tuple[int, int, int] = (15, 41, 66)) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def zip_bytes(files: dict[str, bytes | str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, payload in files.items():
            if isinstance(payload, str):
                payload = payload.encode("utf-8")
            archive.writestr(name, payload)
    return buffer.getvalue()


CHAPTER = """# Measurement

A length of 1.85 m has a unit.

![Caliper](images/vernier.png)

::: {.givens}
**G (Given):** 120 m east.
:::

::: {.workspace}
250 mm = ________ m
:::

::: {.exam-trap}
Do not divide square centimetres by 100.
:::
"""
