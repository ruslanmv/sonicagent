"""Normalize uploaded microphone audio to mono 16 kHz floats."""

from __future__ import annotations

import importlib
import importlib.util
import io
import math
from dataclasses import dataclass

from sonicagent_rt.audio.wav import decode_wav
from sonicagent_rt.stt.errors import AudioTooLong, InvalidAudio, UnsupportedCodec

WHISPER_SAMPLE_RATE = 16000


@dataclass(frozen=True)
class DecodedAudio:
    samples: list[float]
    sample_rate: int
    duration_ms: int
    source_format: str
    source_sample_rate: int
    source_channels: int


def sniff_format(data: bytes, content_type: str | None, filename: str | None) -> str:
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "wav"
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        return "webm"
    if data.startswith(b"OggS"):
        return "ogg"
    if data.startswith(b"ID3") or (len(data) > 1 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):
        return "mp3"
    if len(data) > 11 and data[4:8] == b"ftyp":
        return "mp4"
    hint = f"{content_type or ''} {filename or ''}".lower()
    if "wav" in hint:
        return "wav"
    if any(token in hint for token in ("webm", "ogg", "opus", "mp3", "mp4", "m4a")):
        return "container"
    return "unknown"


def decode_audio(
    data: bytes,
    *,
    content_type: str | None,
    filename: str | None,
    max_seconds: float,
    target_rate: int = WHISPER_SAMPLE_RATE,
) -> DecodedAudio:
    if not data:
        raise InvalidAudio("audio file is empty")
    if max_seconds <= 0 or target_rate <= 0:
        raise InvalidAudio("audio limits are not configured")
    kind = sniff_format(data, content_type, filename)
    if kind == "unknown":
        raise UnsupportedCodec("audio format is not supported; send WAV or WebM/Opus")
    if kind == "wav":
        samples, source_rate, channels = decode_wav(data, max_seconds=max_seconds)
        source_format = "wav"
    else:
        samples, source_rate, channels = _decode_container(data, max_seconds=max_seconds, target_rate=target_rate)
        source_format = kind if kind != "container" else "webm"
        # Container decoding already resamples when PyAV is available.
        if source_rate == target_rate:
            return _pack(samples, target_rate, source_format, source_rate, channels)
    resampled = resample_mono(samples, source_rate, target_rate)
    return _pack(resampled, target_rate, source_format, source_rate, channels)


def resample_mono(samples: list[float], source_rate: int, target_rate: int) -> list[float]:
    if source_rate == target_rate or not samples:
        return list(samples)
    if source_rate <= 0 or target_rate <= 0:
        raise InvalidAudio("sample rate is invalid")
    target_len = int(round(len(samples) * target_rate / source_rate))
    if target_len <= 1:
        return [samples[0]]
    scale = (len(samples) - 1) / (target_len - 1)
    last = len(samples) - 1
    output: list[float] = []
    for index in range(target_len):
        position = index * scale
        left = int(position)
        right = min(left + 1, last)
        fraction = position - left
        output.append(samples[left] * (1.0 - fraction) + samples[right] * fraction)
    return output


def is_silence(samples: list[float], rms_threshold: float) -> bool:
    if not samples:
        return True
    peak = 0.0
    total = 0.0
    for sample in samples:
        magnitude = abs(sample)
        peak = max(peak, magnitude)
        total += sample * sample
    if peak < 0.01:
        return True
    rms = math.sqrt(total / len(samples))
    return rms < rms_threshold


def _pack(
    samples: list[float],
    sample_rate: int,
    source_format: str,
    source_rate: int,
    channels: int,
) -> DecodedAudio:
    if not samples:
        raise InvalidAudio("audio file contains no samples")
    duration_ms = int(round(len(samples) * 1000 / sample_rate))
    return DecodedAudio(
        samples=samples,
        sample_rate=sample_rate,
        duration_ms=duration_ms,
        source_format=source_format,
        source_sample_rate=source_rate,
        source_channels=channels,
    )


def _decode_container(data: bytes, *, max_seconds: float, target_rate: int) -> tuple[list[float], int, int]:
    if importlib.util.find_spec("av") is None:
        raise UnsupportedCodec("WebM/Opus decoding requires the optional PyAV decoder, which is not installed")
    av = importlib.import_module("av")
    try:
        container = av.open(io.BytesIO(data))
    except Exception as exc:
        raise InvalidAudio("audio container could not be decoded") from exc
    try:
        stream = next((item for item in container.streams if item.type == "audio"), None)
        if stream is None:
            raise InvalidAudio("container does not include an audio stream")
        resampler = av.AudioResampler(format="flt", layout="mono", rate=target_rate)
        chunks: list[list[float]] = []
        total = 0
        limit = int((max_seconds + 0.05) * target_rate)

        def consume(converted: object) -> None:
            nonlocal total
            frames = converted if isinstance(converted, list) else [converted]
            for frame in frames:
                if frame is None:
                    continue
                array = frame.to_ndarray().reshape(-1)
                total += int(array.size)
                if total > limit:
                    raise AudioTooLong("recording is longer than the configured maximum")
                chunks.append([float(sample) for sample in array])

        for frame in container.decode(stream):
            consume(resampler.resample(frame))
        consume(resampler.resample(None))
    except (AudioTooLong, InvalidAudio):
        raise
    except Exception as exc:
        raise InvalidAudio("audio container could not be decoded") from exc
    finally:
        container.close()
    samples = [sample for chunk in chunks for sample in chunk]
    if not samples:
        raise InvalidAudio("audio container contains no samples")
    return samples, target_rate, 1
