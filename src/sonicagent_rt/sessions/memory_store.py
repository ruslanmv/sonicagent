"""Concurrency-safe in-memory session store for development and CI."""

from __future__ import annotations

import asyncio

from .models import Session


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()

    async def create(self, session: Session) -> Session:
        async with self._lock:
            if session.session_id in self._sessions:
                raise ValueError("session already exists")
            self._sessions[session.session_id] = session
            return session

    async def get(self, session_id: str) -> Session | None:
        async with self._lock:
            return self._sessions.get(session_id)

    async def delete(self, session_id: str) -> bool:
        async with self._lock:
            return self._sessions.pop(session_id, None) is not None
