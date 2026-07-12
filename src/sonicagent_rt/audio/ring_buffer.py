"""Bounded byte ring buffer used for pre-roll and audio staging."""

from __future__ import annotations

from collections import deque


class RingBuffer:
    def __init__(self, capacity_bytes: int) -> None:
        if capacity_bytes <= 0:
            raise ValueError("capacity_bytes must be positive")
        self.capacity_bytes = capacity_bytes
        self._chunks: deque[bytes] = deque()
        self._size = 0

    @property
    def size_bytes(self) -> int:
        return self._size

    def append(self, data: bytes) -> None:
        chunk = bytes(data)
        if not chunk:
            return
        self._chunks.append(chunk)
        self._size += len(chunk)
        self._trim()

    def _trim(self) -> None:
        while self._size > self.capacity_bytes and self._chunks:
            over = self._size - self.capacity_bytes
            first = self._chunks[0]
            if len(first) <= over:
                self._size -= len(first)
                self._chunks.popleft()
            else:
                self._chunks[0] = first[over:]
                self._size -= over

    def read(self) -> bytes:
        return b"".join(self._chunks)

    def clear(self) -> None:
        self._chunks.clear()
        self._size = 0
