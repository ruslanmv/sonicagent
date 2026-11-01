"""Process-local session store. A restart drops every session."""

from __future__ import annotations

import time
from threading import Lock

from sonicagent_rt.sessions.models import SpeechSession
from sonicagent_rt.stt.errors import RateLimited, Unauthenticated


class MemorySessionStore:
    def __init__(self, *, ttl_sec: int, max_sessions: int) -> None:
        self._ttl_sec = ttl_sec
        self._max_sessions = max_sessions
        self._items: dict[str, SpeechSession] = {}
        self._lock = Lock()

    def put(self, session: SpeechSession) -> None:
        with self._lock:
            self._drop_expired(time.monotonic())
            if session.session_id not in self._items and len(self._items) >= self._max_sessions:
                raise RateLimited("too many realtime sessions are open")
            self._items[session.session_id] = session

    def take(self, session_id: str, resume_token: str, *, now: float | None = None) -> SpeechSession:
        current = time.monotonic() if now is None else now
        with self._lock:
            self._drop_expired(current)
            session = self._items.get(session_id)
            if session is None or not _same(session.resume_token, resume_token):
                raise Unauthenticated("authentication is required")
            if session.expires_at <= current:
                self._items.pop(session_id, None)
                raise Unauthenticated("authentication is required")
            return session

    def discard(self, session_id: str) -> None:
        with self._lock:
            self._items.pop(session_id, None)

    def _drop_expired(self, now: float) -> None:
        expired = [key for key, value in self._items.items() if value.expires_at <= now]
        for key in expired:
            self._items.pop(key, None)


def _same(expected: str, presented: str) -> bool:
    import hashlib
    import hmac

    return hmac.compare_digest(
        hashlib.sha256(expected.encode("utf-8")).digest(),
        hashlib.sha256(presented.encode("utf-8")).digest(),
    )
