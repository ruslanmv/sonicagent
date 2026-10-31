"""In-memory sliding-window limit for batch voice requests."""

from __future__ import annotations

import threading
import time

from sonicagent_rt.stt.errors import RateLimited


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_sec: float = 60.0) -> None:
        self._limit = limit
        self._window = window_sec
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        if self._limit <= 0:
            return
        now = time.monotonic()
        with self._lock:
            recent = [stamp for stamp in self._hits.get(key, []) if now - stamp < self._window]
            if len(recent) >= self._limit:
                self._hits[key] = recent
                raise RateLimited("rate limit exceeded")
            recent.append(now)
            self._hits[key] = recent
