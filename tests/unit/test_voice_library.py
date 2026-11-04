"""HV9. The multilingual voice library, its presets, and one model per ONNX file."""

from __future__ import annotations

import json
import sys
import threading
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sonicagent_rt.api.app_factory import create_app
from sonicagent_rt.api.routes.voices import PRESETS
from sonicagent_rt.config import Settings
from sonicagent_rt.tts.base import TtsStatus
from sonicagent_rt.tts.models import registry_voices, voice_record
from tests.unit.test_speech_stream import _collect, _create, _speech_settings, _url
from tests.unit.test_voice_api import FakeStt, auth, client_for, settings

COMPANION = {"length_scale": 1.16, "noise_scale": 0.8, "noise_w_scale": 0.92}
SECRETARY = {"length_scale": 0.94, "noise_scale": 0.48, "noise_w_scale": 0.6}


def _params(record):
    return {
        "length_scale": record.length_scale,
        "noise_scale": record.noise_scale,
        "noise_w_scale": record.noise_w_scale,
    }


# ── The registry and the documented presets ─────────────────────────


@pytest.mark.parametrize("locale,roles", sorted(PRESETS.items()))
def test_every_documented_preset_is_a_female_registry_voice_with_its_role(locale, roles):
    for role, voice_id in roles.items():
        record = voice_record(voice_id)
        assert record is not None, voice_id
        assert record.role == role
        assert record.locale == locale
        assert record.gender == "female"
        assert _params(record) == (COMPANION if role == "companion" else SECRETARY)


def test_speaker_ids_are_the_documented_ones():
    assert voice_record("es_ES-sharvard-companion").speaker_id == 1
    assert voice_record("es_ES-sharvard-secretary").speaker_id == 1
    assert voice_record("es_ES-sharvard-male").speaker_id == 0
    assert voice_record("fr_FR-upmc-medium").speaker_id == 0  # Jessica
    assert voice_record("fr_FR-upmc-pierre").speaker_id == 1


def test_brazilian_portuguese_is_male_only_and_gets_no_invented_preset():
    pt = [r for r in registry_voices() if r.locale == "pt-BR"]
    assert {r.id for r in pt} == {"pt_BR-edresson-low", "pt_BR-faber-medium"}
    assert all(r.gender == "male" for r in pt)
    assert "pt-BR" not in PRESETS


def test_shared_models_are_one_file():
    def model(voice_id):
        return voice_record(voice_id).model_path

    assert model("it_IT-paola-companion") == model("it_IT-paola-medium")
    assert (
        model("es_ES-sharvard-companion") == model("es_ES-sharvard-secretary") == model("es_ES-sharvard-male")
    )
    assert model("es_MX-ald-companion") == model("es_MX-ald-medium")


# ── GET /v1/voices ───────────────────────────────────────────────────


class LibraryTts:
    def __init__(self, installed, loaded=(), ready=True):
        self._installed = tuple(installed)
        self._loaded = set(loaded)
        self.ready = ready
        self.warmed: list[str] = []

    def describe(self):
        return TtsStatus(True, self.ready, self._installed, None)

    def is_loaded(self, voice_id):
        return voice_id in self._loaded

    def warm(self, voice_id):
        self.warmed.append(voice_id)
        self._loaded.add(voice_id)
        return {"voice_id": voice_id, "cold": True, "ms": 1.0, "load_ms": 1.0}


def test_voices_say_what_this_server_can_play_now():
    tts = LibraryTts(["it_IT-paola-medium", "it_IT-paola-companion"], loaded=["it_IT-paola-medium"])
    with client_for(settings(), FakeStt(), tts) as client:
        body = client.get("/v1/voices").json()
    by_id = {v["id"]: v for v in body["voices"]}
    assert by_id["it_IT-paola-medium"]["state"] == "loaded"
    assert by_id["it_IT-paola-companion"]["state"] == "installed"
    assert by_id["en_US-kristin-medium"]["state"] == "missing"
    assert by_id["it_IT-paola-companion"]["playable"] is True
    assert by_id["en_US-kristin-medium"]["playable"] is False
    assert by_id["it_IT-paola-companion"]["shares_model_with"] == ["it_IT-paola-medium"]
    assert body["presets"]["it-IT"] == {
        "companion": "it_IT-paola-companion",
        "secretary": "it_IT-paola-medium",
    }
    assert body["voice_count"] == 52 and body["tts_ready"] is True


def test_installed_is_not_playable_while_piper_is_not_ready():
    tts = LibraryTts(["it_IT-paola-medium"], ready=False)
    with client_for(settings(), FakeStt(), tts) as client:
        body = client.get("/v1/voices").json()
    assert next(v for v in body["voices"] if v["id"] == "it_IT-paola-medium")["playable"] is False


def test_warm_needs_the_service_key_and_loads_one_voice():
    tts = LibraryTts(["it_IT-paola-companion"])
    with client_for(settings(), FakeStt(), tts) as client:
        anonymous = client.post("/v1/voices/warm", json={"voice_id": "it_IT-paola-companion"})
        warmed = client.post("/v1/voices/warm", headers=auth(), json={"voice_id": "it_IT-paola-companion"})
        unknown = client.post("/v1/voices/warm", headers=auth(), json={"voice_id": "xx_XX-nobody-low"})
    assert anonymous.status_code == 401
    assert warmed.json()["voice_id"] == "it_IT-paola-companion"
    assert tts.warmed == ["it_IT-paola-companion"]
    assert unknown.status_code >= 400


# ── One loaded model per ONNX file ───────────────────────────────────


@pytest.fixture
def fake_piper(tmp_path, monkeypatch):
    loads: list[str] = []
    gate = threading.Event()

    class PiperVoice:
        @classmethod
        def load(cls, model, config_path=None):
            loads.append(Path(model).name)
            gate.wait(0.2)  # long enough for a concurrent request to arrive mid-load
            return cls()

    module = types.ModuleType("piper")
    module.PiperVoice = PiperVoice
    monkeypatch.setitem(sys.modules, "piper", module)
    monkeypatch.setattr("importlib.util.find_spec", lambda name, *a: object() if name == "piper" else None)
    for voice_id in ("it_IT-paola-medium", "es_ES-sharvard-companion"):
        record = voice_record(voice_id)
        (tmp_path / record.model_filename).write_bytes(b"onnx")
        (tmp_path / record.config_filename).write_text(json.dumps({"phoneme_type": "espeak"}))
    from sonicagent_rt.tts.piper_process import PiperSynthesizer

    engine = PiperSynthesizer(Settings(_env_file=None, tts_enabled=True, tts_model_dir=str(tmp_path)))
    return engine, loads


def test_companion_and_secretary_share_one_loaded_model(fake_piper):
    engine, loads = fake_piper
    first = engine.warm("it_IT-paola-medium")
    second = engine.warm("it_IT-paola-companion")
    assert loads == ["it_IT-paola-medium.onnx"]
    assert first["cold"] is True and second["cold"] is False
    assert engine.is_loaded("it_IT-paola-companion")
    assert engine._voice("it_IT-paola-medium") is engine._voice("it_IT-paola-companion")
    assert engine.loaded_models() == 1


def test_two_presets_asking_at_once_load_the_model_once(fake_piper):
    engine, loads = fake_piper
    threads = [
        threading.Thread(target=engine.warm, args=(v,))
        for v in ("es_ES-sharvard-companion", "es_ES-sharvard-secretary", "es_ES-sharvard-male")
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert loads == ["es_ES-sharvard-medium.onnx"]


def test_warming_one_voice_does_not_preload_the_catalogue(fake_piper):
    engine, loads = fake_piper
    engine.warm("it_IT-paola-companion")
    assert engine.loaded_models() == 1
    assert not engine.is_loaded("es_ES-sharvard-companion")


# ── The speech socket: a voice per phrase, warm, and per-voice metrics ──


class RecordingTts(LibraryTts):
    def __init__(self):
        super().__init__(["it_IT-paola-medium", "it_IT-paola-companion", "en_US-lessac-medium"])
        self.spoken: list[str] = []

    def iter_pcm(self, text, *, voice, language, cancel):
        self.spoken.append(voice)
        yield 22050, b"\x00\x00" * 882


def test_a_phrase_can_name_its_voice_and_profile_without_a_new_session():
    tts = RecordingTts()
    app = create_app(_speech_settings())
    app.state.stt = FakeStt()
    app.state.tts = tts
    with TestClient(app) as client:
        created = _create(client, mode="tts_only", language="it", voice_id="it_IT-paola-medium").json()
        with client.websocket_connect(_url(created)) as socket:
            socket.receive_json()
            socket.send_text(json.dumps({"type": "tts.speak", "text": "Buongiorno.", "turn_id": "s"}))
            secretary, _ = _collect(socket)
            socket.send_text(
                json.dumps(
                    {
                        "type": "tts.speak",
                        "text": "Ciao!",
                        "turn_id": "c",
                        "voice_id": "it_IT-paola-companion",
                    }
                )
            )
            companion, _ = _collect(socket)
            socket.send_text(
                json.dumps(
                    {"type": "tts.speak", "text": "x", "turn_id": "bad", "voice_id": "xx_XX-ghost-low"}
                )
            )
            refused, _ = _collect(socket, stop={"session.error"})
            socket.send_text(json.dumps({"type": "tts.warm", "voice_id": "en_US-lessac-medium"}))
            warmed, _ = _collect(socket, stop={"tts.warmed"})
    assert tts.spoken == ["it_IT-paola-medium", "it_IT-paola-companion"]
    started = [e for e in secretary + companion if e["type"] == "tts.started"]
    assert [(e["voice_id"], e["role"]) for e in started] == [
        ("it_IT-paola-medium", "secretary"),
        ("it_IT-paola-companion", "companion"),
    ]
    metrics = next(e for e in companion if e["type"] == "metrics.turn")
    assert metrics["voice_id"] == "it_IT-paola-companion" and metrics["role"] == "companion"
    assert metrics["rtf"] is not None and metrics["synth_ms"] >= 0
    assert refused[-1]["code"] == "voice_unavailable"
    assert warmed[-1]["voice_id"] == "en_US-lessac-medium"
