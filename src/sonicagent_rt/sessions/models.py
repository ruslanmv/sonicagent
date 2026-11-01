"""In-memory realtime session records. Tokens are not written to logs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SpeechSession:
    session_id: str
    resume_token: str
    language: str
    voice_id: str
    expires_at: float
