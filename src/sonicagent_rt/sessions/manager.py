"""Create and authenticate short-lived realtime sessions."""

from __future__ import annotations

import secrets
import time
from uuid import uuid4

from sonicagent_rt.config import Settings
from sonicagent_rt.sessions.memory_store import MemorySessionStore
from sonicagent_rt.sessions.models import SpeechSession
from sonicagent_rt.stt.errors import InvalidRequest
from sonicagent_rt.tts.models import validate_voice_id


class SessionManager:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._store = MemorySessionStore(
            ttl_sec=settings.session_ttl_sec,
            max_sessions=settings.max_concurrent_sessions,
        )

    def create(self, *, language: str, voice_id: str) -> SpeechSession:
        language = language.strip().lower() or "auto"
        allowed = set(self._settings.parsed_stt_languages()) | {"auto"}
        if language not in allowed:
            raise InvalidRequest("language is not enabled")
        voice = validate_voice_id(voice_id)
        now = time.monotonic()
        session = SpeechSession(
            session_id=f"ses_{uuid4().hex}",
            resume_token=secrets.token_urlsafe(32),
            language=language,
            voice_id=voice,
            expires_at=now + self._settings.session_ttl_sec,
        )
        self._store.put(session)
        return session

    def authenticate(self, session_id: str, resume_token: str) -> SpeechSession:
        return self._store.take(session_id, resume_token)

    def acquire(self, session_id: str, resume_token: str) -> tuple[SpeechSession, bool]:
        return self._store.acquire(session_id, resume_token)

    def release(self, session_id: str) -> None:
        self._store.release(session_id)

    def discard(self, session_id: str) -> None:
        self._store.discard(session_id)
