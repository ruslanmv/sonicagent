"""Short-lived speech-only sessions. These sessions never call the language model."""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from threading import Lock

from sonicagent_rt.stt.errors import RateLimited, Unauthenticated

MODES = ("stt_only", "tts_only", "duplex_speech")


@dataclass
class SpeechStreamSession:
    session_id: str
    resume_token: str
    mode: str
    language: str | None
    voice_id: str
    stt_provider: str
    expires_at: float
    held: bool = False


class SpeechStreamStore:
    def __init__(self, *, ttl_sec: int, max_sessions: int) -> None:
        self._ttl_sec = ttl_sec
        self._max_sessions = max_sessions
        self._items: dict[str, SpeechStreamSession] = {}
        self._lock = Lock()

    def put(self, session: SpeechStreamSession) -> None:
        with self._lock:
            self._drop_expired(time.monotonic())
            if session.session_id not in self._items and len(self._items) >= self._max_sessions:
                raise RateLimited("too many speech sessions are open")
            self._items[session.session_id] = session

    def acquire(self, session_id: str, resume_token: str) -> SpeechStreamSession:
        current_time = time.monotonic()
        with self._lock:
            self._drop_expired(current_time)
            current = self._items.get(session_id)
            if current is None or not _same(current.resume_token, resume_token):
                raise Unauthenticated("authentication is required")
            if current.expires_at <= current_time:
                self._items.pop(session_id, None)
                raise Unauthenticated("authentication is required")
            if current.held:
                raise RateLimited("session is already connected")
            current.held = True
            return current

    def release(self, session_id: str) -> None:
        with self._lock:
            current = self._items.get(session_id)
            if current is not None:
                current.held = False

    def _drop_expired(self, now: float) -> None:
        expired = [key for key, value in self._items.items() if value.expires_at <= now]
        for key in expired:
            self._items.pop(key, None)


def _same(expected: str, presented: str) -> bool:
    return hmac.compare_digest(
        hashlib.sha256(expected.encode("utf-8")).digest(),
        hashlib.sha256(presented.encode("utf-8")).digest(),
    )
