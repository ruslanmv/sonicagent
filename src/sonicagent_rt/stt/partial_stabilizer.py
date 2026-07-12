"""Stabilize partial STT hypotheses by emitting common prefixes."""

from __future__ import annotations


class PartialStabilizer:
    def __init__(self, min_repeats: int = 2) -> None:
        if min_repeats < 1:
            raise ValueError("min_repeats must be positive")
        self.min_repeats = min_repeats
        self._last = ""
        self._count = 0
        self.stable = ""

    def update(self, hypothesis: str) -> str:
        normalized = " ".join(hypothesis.split())
        self._count = self._count + 1 if normalized == self._last else 1
        self._last = normalized
        if self._count >= self.min_repeats and normalized.startswith(self.stable):
            self.stable = normalized
        return self.stable
