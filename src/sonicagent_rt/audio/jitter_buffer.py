"""Small bounded sequence-aware jitter buffer."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class JitterBuffer:
    capacity_frames: int
    expected_sequence: int = 0
    _frames: dict[int, bytes] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.capacity_frames <= 0:
            raise ValueError("capacity_frames must be positive")

    def push(self, sequence: int, payload: bytes) -> None:
        if sequence < self.expected_sequence:
            return
        if len(self._frames) >= self.capacity_frames and sequence not in self._frames:
            raise BufferError("jitter buffer full")
        self._frames[sequence] = bytes(payload)

    def pop_ready(self) -> list[bytes]:
        ready: list[bytes] = []
        while self.expected_sequence in self._frames:
            ready.append(self._frames.pop(self.expected_sequence))
            self.expected_sequence = (self.expected_sequence + 1) & 0xFFFFFFFF
        return ready
