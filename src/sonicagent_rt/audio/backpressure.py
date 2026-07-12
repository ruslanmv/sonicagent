"""Backpressure policy for bounded outbound audio queues."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BackpressureDecision:
    accepted: bool
    reason: str = ""
    purge: bool = False


@dataclass
class BackpressurePolicy:
    max_queued_ms: int
    slow_client_ms: int | None = None

    def __post_init__(self) -> None:
        if self.max_queued_ms <= 0:
            raise ValueError("max_queued_ms must be positive")
        if self.slow_client_ms is None:
            self.slow_client_ms = self.max_queued_ms * 2

    def evaluate(self, queued_ms: int, incoming_ms: int) -> BackpressureDecision:
        next_total = queued_ms + incoming_ms
        if next_total <= self.max_queued_ms:
            return BackpressureDecision(True)
        if next_total >= int(self.slow_client_ms or 0):
            return BackpressureDecision(False, "slow-client", purge=True)
        return BackpressureDecision(False, "queue-full")
