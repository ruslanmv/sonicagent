"""HV9 with real Piper: the profiles really change the speech, and shared models load once.

Skipped unless piper-tts and the voice files are in /tmp/sonic-voices/tts (the same place
test_piper_synthesis.py reads). Files from ruslanmv/hp-piper-voices, checked against the
registry's SHA-256 before use.
"""

from __future__ import annotations

import hashlib
import threading
from pathlib import Path

import pytest

from sonicagent_rt.tts.models import voice_record

pytestmark = pytest.mark.integration
pytest.importorskip("piper")

VOICES = Path("/tmp/sonic-voices/tts")
NEEDED = ("it_IT-paola-medium", "es_ES-sharvard-companion")


def _engine():
    for voice_id in NEEDED:
        if not (VOICES / voice_record(voice_id).model_filename).is_file():
            pytest.skip("Piper voice files are not installed in /tmp/sonic-voices/tts")
    from sonicagent_rt.config import Settings
    from sonicagent_rt.tts.piper_process import PiperSynthesizer

    return PiperSynthesizer(
        Settings(_env_file=None, tts_enabled=True, tts_model_dir=str(VOICES), tts_max_chars=500)
    )


def _seconds(engine, voice_id, text):
    samples = 0
    rate = 1
    for rate, pcm in engine.iter_pcm(text, voice=voice_id, language=None, cancel=threading.Event()):
        samples += len(pcm) // 2
    return samples / rate


def test_the_files_are_the_registry_files():
    for voice_id in NEEDED:
        record = voice_record(voice_id)
        path = VOICES / record.model_filename
        if not path.is_file():
            pytest.skip("voice files are not installed")
        import json

        registry = json.loads(Path("model_registry/voices.json").read_text())
        expected = next(v["model_sha256"] for v in registry["voices"] if v["id"] == voice_id)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected


def test_companion_is_slower_than_secretary_on_the_same_model():
    engine = _engine()
    text = "Buongiorno. Vediamo insieme gli impegni di oggi."
    # Piper's noise makes each run differ: measured over 12 single runs the ratio was 1.05-1.21
    # (mean ~1.15, below length_scale's nominal 1.16/0.94 = 1.23 because not every pause scales).
    # Five runs averaged stay well inside the bound.
    secretary = sum(_seconds(engine, "it_IT-paola-medium", text) for _ in range(5))
    companion = sum(_seconds(engine, "it_IT-paola-companion", text) for _ in range(5))
    assert 1.07 < companion / secretary < 1.35
    assert engine.loaded_models() == 1


def test_speaker_id_selects_a_different_voice_in_one_model():
    engine = _engine()
    text = "Hola, estoy aquí contigo."
    female = b"".join(
        pcm
        for _r, pcm in engine.iter_pcm(
            text, voice="es_ES-sharvard-companion", language=None, cancel=threading.Event()
        )
    )
    male = b"".join(
        pcm
        for _r, pcm in engine.iter_pcm(
            text, voice="es_ES-sharvard-male", language=None, cancel=threading.Event()
        )
    )
    assert female != male
    assert engine.loaded_models() == 1
