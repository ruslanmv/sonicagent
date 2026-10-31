"""Decode PCM WAV microphone uploads with the standard library."""

from __future__ import annotations

import io
import wave

from sonicagent_rt.stt.errors import AudioTooLong, InvalidAudio


def decode_wav(data: bytes, *, max_seconds: float) -> tuple[list[float], int, int]:
    """Return mono float samples, source sample rate, and channel count."""
    if not data:
        raise InvalidAudio("audio file is empty")
    try:
        handle = wave.open(io.BytesIO(data), "rb")
    except wave.Error as exc:
        raise InvalidAudio("audio is not a valid PCM WAV file") from exc
    with handle:
        channels = handle.getnchannels()
        rate = handle.getframerate()
        width = handle.getsampwidth()
        frames = handle.getnframes()
        if channels < 1 or channels > 8 or rate <= 0 or width not in {1, 2, 3, 4}:
            raise InvalidAudio("WAV layout is not supported")
        if frames <= 0:
            raise InvalidAudio("WAV file contains no samples")
        if frames / rate > max_seconds + 0.05:
            raise AudioTooLong("recording is longer than the configured maximum")
        max_frames = int((max_seconds + 0.05) * rate) + 1
        raw = handle.readframes(max_frames)
        if handle.readframes(1):
            raise AudioTooLong("recording is longer than the configured maximum")
    if not raw:
        raise InvalidAudio("WAV file contains no samples")
    return _pcm_to_mono_floats(raw, width=width, channels=channels), rate, channels


def _pcm_to_mono_floats(raw: bytes, *, width: int, channels: int) -> list[float]:
    frame_width = width * channels
    if len(raw) % frame_width != 0:
        raise InvalidAudio("WAV data ends in a partial frame")
    count = len(raw) // frame_width
    samples: list[float] = []
    for index in range(count):
        base = index * frame_width
        mixed = 0.0
        for channel in range(channels):
            chunk = raw[base + channel * width : base + (channel + 1) * width]
            mixed += _sample_to_float(chunk, width)
        samples.append(max(-1.0, min(1.0, mixed / channels)))
    return samples


def _sample_to_float(chunk: bytes, width: int) -> float:
    if width == 1:
        return (chunk[0] - 128) / 128.0
    if width == 2:
        return int.from_bytes(chunk, "little", signed=True) / 32768.0
    if width == 3:
        value = int.from_bytes(chunk, "little", signed=False)
        if value & 0x800000:
            value -= 0x1000000
        return value / 8388608.0
    return int.from_bytes(chunk, "little", signed=True) / 2147483648.0
