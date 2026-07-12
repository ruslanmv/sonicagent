"""Deterministic linear PCM16 mono resampler."""

from __future__ import annotations

from .pcm import pcm16_to_floats, floats_to_pcm16


def resample_pcm16_mono(data: bytes, *, source_rate: int, target_rate: int) -> bytes:
    if source_rate <= 0 or target_rate <= 0:
        raise ValueError("sample rates must be positive")
    if source_rate == target_rate:
        return bytes(data)
    samples = pcm16_to_floats(data)
    if not samples:
        return b""
    target_len = max(1, round(len(samples) * target_rate / source_rate))
    if target_len == 1:
        return floats_to_pcm16([samples[0]])
    scale = (len(samples) - 1) / (target_len - 1)
    out: list[float] = []
    for idx in range(target_len):
        pos = idx * scale
        left = int(pos)
        right = min(left + 1, len(samples) - 1)
        frac = pos - left
        out.append(samples[left] * (1 - frac) + samples[right] * frac)
    return floats_to_pcm16(out)
