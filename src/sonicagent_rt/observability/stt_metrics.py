"""Prometheus metrics for batch transcription.

Labels stay low-cardinality. Audio and transcript text are never label values.
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram

STT_REQUESTS = Counter(
    "sonicagent_stt_requests_total",
    "Batch speech-to-text requests.",
    labelnames=("result", "code"),
)
STT_PROCESSING_SECONDS = Histogram(
    "sonicagent_stt_processing_seconds",
    "Transcription wall time in seconds.",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 30, 60),
)
STT_AUDIO_SECONDS = Histogram(
    "sonicagent_stt_audio_seconds",
    "Decoded audio duration in seconds.",
    buckets=(0.2, 0.5, 1, 2, 5, 10, 15, 30),
)
TTS_REQUESTS = Counter(
    "sonicagent_tts_requests_total",
    "Batch speech-synthesis requests.",
    labelnames=("result", "code"),
)


def observe_stt(result: str, code: str, processing_sec: float, audio_sec: float) -> None:
    STT_REQUESTS.labels(result=result, code=code).inc()
    if result == "ok":
        STT_PROCESSING_SECONDS.observe(max(0.0, processing_sec))
        STT_AUDIO_SECONDS.observe(max(0.0, audio_sec))


def observe_tts(result: str, code: str) -> None:
    TTS_REQUESTS.labels(result=result, code=code).inc()
