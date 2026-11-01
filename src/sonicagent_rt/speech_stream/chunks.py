"""Turn Piper sentence audio, or one finished WAV, into PCM16 buffers."""

from __future__ import annotations

from collections.abc import Iterator

from sonicagent_rt.audio.wav import decode_wav
from sonicagent_rt.audio.pcm import floats_to_pcm16


def iter_pcm16(tts: object, text: str, *, voice: str, language: str | None, cancel: object) -> Iterator[tuple[int, bytes]]:
    """Yield ``(sample_rate, pcm16)``. Sentence chunks stay separate when the engine provides them."""
    method = getattr(tts, "iter_pcm", None)
    if callable(method):
        yield from method(text, voice=voice, language=language, cancel=cancel)
        return
    speech = tts.synthesize(text, voice=voice, language=language, cancel=cancel)  # type: ignore[attr-defined]
    samples, rate, _channels = decode_wav(speech.wav, max_seconds=120)
    yield rate, floats_to_pcm16(samples)


def split_frames(pcm: bytes, sample_rate: int, frame_ms: int) -> Iterator[bytes]:
    samples = max(1, int(sample_rate * frame_ms / 1000))
    step = samples * 2
    for offset in range(0, len(pcm), step):
        piece = pcm[offset : offset + step]
        if piece:
            yield piece
