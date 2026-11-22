"""Compile the Typst template once so a broken template fails the image build."""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

from physics_studio.staging import stage_zip


def main() -> None:
    destination = Path(sys.argv[1] if len(sys.argv) > 1 else "/opt/warm")
    destination.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "bab-01.qmd",
            "# Warm\n\n## Section\n\n::: {.objectives}\n- One.\n:::\n\n"
            "::: {.worked-example}\nGiven a metre.\n:::\n\n::: {.remember}\nUnits.\n:::\n\n"
            "::: {.review}\n1. Q.\n:::\n",
        )
    stage_zip(buffer.getvalue(), destination)


if __name__ == "__main__":
    main()
