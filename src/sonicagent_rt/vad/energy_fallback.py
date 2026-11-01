"""RMS endpointing for 16-bit microphone audio.

This is the VAD that runs when a Silero ONNX file is not configured. It does
not download a model and it does not invent speech probabilities.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class EndpointEvent:
    kind: str
    samples: list[float]


class EnergyEndpoint:
    def __init__(
        self,
        *,
        threshold: float,
        min_speech_ms: int,
        min_silence_ms: int,
        pre_roll_ms: int,
        max_utterance_sec: float,
        sample_rate: int,
    ) -> None:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        self.threshold = threshold
        self.min_speech_ms = min_speech_ms
        self.min_silence_ms = min_silence_ms
        self.max_samples = max(1, int(max_utterance_sec * sample_rate))
        self.sample_rate = sample_rate
        self._pre_roll: deque[float] = deque(maxlen=max(1, int(pre_roll_ms * sample_rate / 1000)))
        self._pending: list[float] = []
        self._speech_ms = 0.0
        self._silence_ms = 0.0
        self._in_speech = False
        self._utterance: list[float] = []

    def push(self, samples: list[float]) -> list[EndpointEvent]:
        events: list[EndpointEvent] = []
        if not samples:
            return events
        duration_ms = len(samples) * 1000 / self.sample_rate
        rms = _rms(samples)
        if rms >= self.threshold:
            self._speech_ms += duration_ms
            self._silence_ms = 0.0
            self._pending.extend(samples)
            if not self._in_speech and self._speech_ms >= self.min_speech_ms:
                self._in_speech = True
                self._utterance = list(self._pre_roll) + self._pending
                self._pending = []
                self._pre_roll.clear()
                events.append(EndpointEvent("started", []))
            elif self._in_speech:
                self._utterance.extend(samples)
        else:
            self._silence_ms += duration_ms
            self._speech_ms = 0.0
            self._pending = []
            if self._in_speech:
                self._utterance.extend(samples)
                if self._silence_ms >= self.min_silence_ms or len(self._utterance) >= self.max_samples:
                    events.append(self._finish())
            else:
                self._pre_roll.extend(samples)
        if self._in_speech and len(self._utterance) >= self.max_samples:
            events.append(self._finish())
        return events

    def flush(self) -> list[EndpointEvent]:
        if self._in_speech and self._utterance:
            return [self._finish()]
        return []

    def _finish(self) -> EndpointEvent:
        samples = self._utterance
        self._utterance = []
        self._pending = []
        self._in_speech = False
        self._speech_ms = 0.0
        self._silence_ms = 0.0
        return EndpointEvent("utterance", samples)


def _rms(samples: list[float]) -> float:
    if not samples:
        return 0.0
    total = 0.0
    for sample in samples:
        total += sample * sample
    return (total / len(samples)) ** 0.5
