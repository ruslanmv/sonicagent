"""PCM16 validation and conversion helpers."""

from __future__ import annotations

import array

PCM16_MIN = -32768
PCM16_MAX = 32767


def validate_pcm16(data: bytes, *, channels: int = 1) -> None:
    if channels < 1:
        raise ValueError("channels must be positive")
    if len(data) % (2 * channels) != 0:
        raise ValueError("PCM16 payload must contain whole samples for all channels")


def floats_to_pcm16(samples: list[float] | tuple[float, ...]) -> bytes:
    out = array.array("h")
    for sample in samples:
        clipped = max(-1.0, min(1.0, float(sample)))
        out.append(int(round(clipped * PCM16_MAX)) if clipped >= 0 else int(round(clipped * -PCM16_MIN)))
    if out.itemsize != 2:
        raise RuntimeError("platform does not provide 16-bit signed array samples")
    return out.tobytes()


def pcm16_to_floats(data: bytes) -> list[float]:
    validate_pcm16(data)
    arr = array.array("h")
    arr.frombytes(data)
    return [
        max(-1.0, sample / PCM16_MAX) if sample >= 0 else max(-1.0, sample / -PCM16_MIN) for sample in arr
    ]
