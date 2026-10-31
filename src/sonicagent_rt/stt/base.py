"""Batch speech-to-text types shared by the API and the Whisper adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SttStatus:
    available: bool
    ready: bool
    model: str
    device: str
    compute_type: str
    languages: tuple[str, ...]
    reason: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "available": self.available,
            "ready": self.ready,
            "model": self.model,
            "device": self.device,
            "compute_type": self.compute_type,
            "languages": list(self.languages),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class Transcript:
    text: str
    language: str
    model: str
    duration_ms: int
    is_final: bool = True

    def as_dict(self, request_id: str) -> dict[str, object]:
        return {
            "text": self.text,
            "language": self.language,
            "model": self.model,
            "is_final": self.is_final,
            "request_id": request_id,
            "duration_ms": self.duration_ms,
        }


class SttEngine(Protocol):
    def describe(self) -> SttStatus:
        """Report whether this process can transcribe, without loading weights."""

    def warmup(self) -> None:
        """Load the configured model. May download only when explicitly allowed."""

    def transcribe(
        self,
        samples: list[float],
        *,
        sample_rate: int,
        language: str | None,
        model: str,
        request_id: str,
        cancel: object,
    ) -> Transcript:
        """Transcribe mono audio. ``cancel`` is a ``threading.Event``."""
