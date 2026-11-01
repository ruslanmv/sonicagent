"""Decoder tests that do not load Whisper."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from sonicagent_rt.audio.decode import decode_audio, is_silence
from sonicagent_rt.stt.errors import AudioTooLong, InvalidAudio, UnsupportedCodec
from sonicagent_rt.stt.language_detection import normalize_language
from sonicagent_rt.stt.models import canonical_size, public_model_id

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "audio"


def test_wav_fixture_resamples_to_16k() -> None:
    decoded = decode_audio(
        (FIXTURES / "en_hello.wav").read_bytes(),
        content_type="audio/wav",
        filename="en_hello.wav",
        max_seconds=15,
    )
    assert decoded.sample_rate == 16000
    assert decoded.source_sample_rate == 22050
    assert decoded.source_channels == 1
    assert 2500 <= decoded.duration_ms <= 3200
    assert is_silence(decoded.samples, 0.005) is False


def test_silence_fixture_is_detected() -> None:
    decoded = decode_audio(
        (FIXTURES / "silence_1s.wav").read_bytes(),
        content_type="audio/wav",
        filename="silence.wav",
        max_seconds=15,
    )
    assert is_silence(decoded.samples, 0.005) is True


def test_rejects_empty_unknown_and_long_header() -> None:
    with pytest.raises(InvalidAudio):
        decode_audio(b"", content_type="audio/wav", filename="empty.wav", max_seconds=15)
    with pytest.raises(UnsupportedCodec):
        decode_audio(b"not-audio", content_type="application/octet-stream", filename="x.bin", max_seconds=15)
    with pytest.raises(InvalidAudio):
        decode_audio(b"RIFF\x00\x00\x00\x00WAVE", content_type="audio/wav", filename="bad.wav", max_seconds=15)


def test_duration_limit() -> None:
    payload = (FIXTURES / "silence_1s.wav").read_bytes()
    with pytest.raises(AudioTooLong):
        decode_audio(payload, content_type="audio/wav", filename="silence.wav", max_seconds=0.2)


def test_language_and_model_names() -> None:
    assert normalize_language("EN-us", allowed=["en", "it"], default="auto") == "en"
    assert normalize_language("auto", allowed=["en", "it"], default="en") is None
    assert public_model_id("tiny") == "whisper-tiny"
    assert canonical_size("whisper-base") == "base"
    with pytest.raises(Exception):
        canonical_size("tiny.en")


@pytest.mark.skipif(importlib.util.find_spec("av") is None, reason="PyAV decoder is not installed")
def test_webm_fixture_decodes() -> None:
    decoded = decode_audio(
        (FIXTURES / "en_hello.webm").read_bytes(),
        content_type="audio/webm;codecs=opus",
        filename="en_hello.webm",
        max_seconds=15,
    )
    assert decoded.source_format == "webm"
    assert decoded.sample_rate == 16000
    assert decoded.duration_ms > 1000


@pytest.mark.skipif(importlib.util.find_spec("av") is None, reason="PyAV decoder is not installed")
def test_corrupt_webm_is_invalid() -> None:
    with pytest.raises(InvalidAudio):
        decode_audio(
            b"\x1a\x45\xdf\xa3not-a-real-webm",
            content_type="audio/webm",
            filename="broken.webm",
            max_seconds=15,
        )
