"""Batch text-to-speech types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TtsStatus:
    available: bool
    ready: bool
    voices: tuple[str, ...]
    reason: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "available": self.available,
            "ready": self.ready,
            "voices": list(self.voices),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class SynthesizedSpeech:
    wav: bytes
    voice: str
    sample_rate: int


class TtsEngine(Protocol):
    def describe(self) -> TtsStatus:
        """Report whether real synthesis is possible."""

    def synthesize(self, text: str, *, voice: str, language: str | None, cancel: object) -> SynthesizedSpeech:
        """Return a WAV payload. ``cancel`` is a ``threading.Event``."""
