"""Real faster-whisper CPU inference. Skipped unless the model extra is installed."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from sonicagent_rt.stt.model_store import install_whisper_model

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "audio"
pytest.importorskip("faster_whisper")


def _words(text: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() or char.isspace() else " " for char in text)
    return " ".join(cleaned.split())


@pytest.fixture(scope="module")
def tiny_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    cache = Path("/tmp/sonic-models")
    if not (cache / "stt" / "tiny" / "model.bin").is_file():
        cache = tmp_path_factory.mktemp("whisper")
    return install_whisper_model("tiny", cache)


@pytest.fixture(scope="module")
def api(tiny_dir: Path):
    from fastapi.testclient import TestClient

    from sonicagent_rt.api.app_factory import create_app
    from sonicagent_rt.config import Settings

    key = "i" * 16
    app = create_app(
        Settings(
            _env_file=None,
            api_key=key,
            environment="development",
            auth_mode="development",
            voice_enabled=True,
            stt_model="tiny",
            stt_model_path=str(tiny_dir),
            stt_device="cpu",
            stt_compute_type="int8",
            stt_warmup=True,
            stt_allow_download=False,
            stt_vad_filter=False,
            max_audio_seconds=15,
            max_upload_bytes=2_097_152,
            stt_timeout_sec=60,
            stt_rate_limit_per_minute=100,
            stt_max_concurrency=2,
            store_audio=False,
            store_transcripts=False,
            log_transcript_content=False,
        )
    )
    with TestClient(app) as client:
        deadline = time_deadline(40)
        ready = {}
        while not time_reached(deadline):
            ready = client.get("/health/ready").json()
            if ready.get("ready") is True:
                break
            sleep_brief()
        assert ready.get("ready") is True, ready
        assert ready["stt"]["device"] == "cpu"
        assert ready["stt"]["compute_type"] == "int8"
        client.headers.update({"Authorization": f"Bearer {key}"})
        yield client


def time_deadline(seconds: float) -> float:
    import time

    return time.monotonic() + seconds


def time_reached(deadline: float) -> bool:
    import time

    return time.monotonic() >= deadline


def sleep_brief() -> None:
    import time

    time.sleep(0.2)


def _post(api, name: str, language: str, content_type: str):
    payload = (FIXTURES / name).read_bytes()
    return api.post(
        "/v1/audio/transcriptions",
        data={"language": language, "model": "whisper-tiny"},
        files={"file": (name, payload, content_type)},
    )


def test_english_and_italian_cpu_inference(api) -> None:
    english = _post(api, "en_hello.wav", "en", "audio/wav")
    italian = _post(api, "it_ciao.wav", "it", "audio/wav")
    assert english.status_code == 200, english.text
    assert italian.status_code == 200, italian.text
    assert _words(english.json()["text"]) == "hello can you help me"
    assert _words(italian.json()["text"]) == "ciao come stai"
    assert english.json()["language"] == "en"
    assert italian.json()["language"] == "it"
    assert english.json()["model"] == "whisper-tiny"
    assert italian.json()["model"] == "whisper-tiny"
    assert english.json()["is_final"] is True
    assert "scaffold" not in english.json()["text"].lower()
    assert english.json()["text"] != italian.json()["text"]


def test_silence_is_empty_and_corrupt_files_fail(api) -> None:
    silence = _post(api, "silence_1s.wav", "en", "audio/wav")
    assert silence.status_code == 200
    assert silence.json()["text"] == ""
    corrupt = api.post(
        "/v1/audio/transcriptions",
        files={"file": ("bad.wav", b"RIFF\x00\x00\x00\x00WAVEjunk", "audio/wav")},
    )
    assert corrupt.status_code == 422
    assert corrupt.json()["error"]["code"] == "invalid_audio"


@pytest.mark.skipif(importlib.util.find_spec("av") is None, reason="PyAV decoder is not installed")
def test_webm_english_inference(api) -> None:
    response = _post(api, "en_hello.webm", "en", "audio/webm;codecs=opus")
    assert response.status_code == 200, response.text
    assert _words(response.json()["text"]) == "hello can you help me"


def test_two_real_requests_both_succeed(api) -> None:
    first = _post(api, "en_hello.wav", "en", "audio/wav")
    second = _post(api, "it_ciao.wav", "it", "audio/wav")
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["text"] != second.json()["text"]
