"""Deterministic model stand-in for dry runs and tests."""

from __future__ import annotations


class MockGemini:
    """Returns a short section that cycles through the three Gold Standard boxes."""

    def __init__(self):
        self.calls: list[str] = []

    def generate(self, *, system: str, user: str) -> str:
        self.calls.append(user)
        index = len(self.calls)
        if index % 3 == 1:
            box = "::: {.givens}\n**G (Given):** 120 m east and 50 m north.\n:::\n"
        elif index % 3 == 2:
            box = "::: {.workspace}\n250 mm = ________ m\n\nTeacher stamp: [ ] L1 [ ] L2 [ ] L3\n:::\n"
        else:
            box = "::: {.exam-trap}\nDividing 5 cm squared by 100 is not a conversion to square metres.\n:::\n"
        return box + "\nA measurement is a number multiplied by a unit.\n"
