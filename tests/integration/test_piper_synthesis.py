"""Real Piper WAV synthesis. Skipped unless piper-tts and the voice files exist."""

from __future__ import annotations

import importlib.util
import io
import wave
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

pytest.importorskip("piper")

VOICES = Path("/tmp/sonic-voices/tts")


def test_lessac_and_paola_write_playable_wav() -> None:
    if not (VOICES / "en_US-lessac-medium.onnx").is_file():
        pytest.skip("Piper voice files are not installed in /tmp/sonic-voices/tts")
    from sonicagent_rt.config import Settings
    from sonicagent_rt.tts.piper_process import PiperSynthesizer

    engine = PiperSynthesizer(
        Settings(_env_file=None, tts_enabled=True, tts_model_dir=str(VOICES), tts_max_chars=200)
    )
    status = engine.describe()
    assert status.available is True
    assert status.ready is True
    assert "en_US-lessac-medium" in status.voices
    assert "it_IT-paola-medium" in status.voices
    english = engine.synthesize("hello", voice="en_US-lessac-medium", language="en", cancel=_idle())
    italian = engine.synthesize("Ciao.", voice="it_IT-paola-medium", language="it", cancel=_idle())
    assert _duration(english.wav) > 0.2
    assert _duration(italian.wav) > 0.2
    assert english.wav != italian.wav
    assert english.sample_rate == 22050
    assert italian.sample_rate == 22050


def _duration(payload: bytes) -> float:
    with wave.open(io.BytesIO(payload), "rb") as handle:
        return handle.getnframes() / handle.getframerate()


def _idle():
    import threading

    return threading.Event()


def test_piper_library_import_name() -> None:
    assert importlib.util.find_spec("piper") is not None
