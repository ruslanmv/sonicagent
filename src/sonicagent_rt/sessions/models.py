"""Session data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .state import SessionState


@dataclass
class Session:
    session_id: str
    resume_token: str
    state: SessionState = SessionState.CREATED
    language: str = "en"
    voice_id: str = "en_US-lessac-medium"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
