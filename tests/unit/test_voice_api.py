"""Unit tests for batch STT/TTS HTTP behavior using a fake acoustic model."""

from __future__ import annotations

import io
import threading
import time
import wave
from typing import Any

from fastapi.testclient import TestClient

from sonicagent_rt.api.app_factory import create_app
from sonicagent_rt.config import Settings
from sonicagent_rt.stt.base import SttStatus, Transcript
from sonicagent_rt.stt.errors import Cancelled, ModelUnavailable, RateLimited
from sonicagent_rt.tts.base import SynthesizedSpeech, TtsStatus

DEV_KEY = "d" * 16
PROD_KEY = "p" * 32


def settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "_env_file": None,
        "api_key": DEV_KEY,
        "environment": "development",
        "auth_mode": "development",
        "voice_enabled": True,
        "stt_warmup": False,
        "stt_model": "tiny",
        "stt_allow_download": False,
        "stt_device": "cpu",
        "stt_compute_type": "int8",
        "max_audio_seconds": 15,
        "max_upload_bytes": 2_097_152,
        "stt_timeout_sec": 2,
        "stt_rate_limit_per_minute": 1000,
        "tts_enabled": False,
        "store_audio": False,
        "store_transcripts": False,
        "log_transcript_content": False,
    }
    values.update(overrides)
    return Settings(**values)


def wav_bytes(samples: list[int], rate: int = 16000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        frames = b"".join(int(sample).to_bytes(2, "little", signed=True) for sample in samples)
        handle.writeframes(frames)
    return buffer.getvalue()


def loud_wav() -> bytes:
    return wav_bytes([8000, -8000] * 4000)


def auth(key: str = DEV_KEY) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


class FakeStt:
    def __init__(self, *, ready: bool = True, available: bool = True, reason: str | None = None) -> None:
        self.calls: list[int] = []
        self._ready = ready
        self._available = available
        self._reason = reason

    def describe(self) -> SttStatus:
        return SttStatus(self._available, self._ready, "whisper-tiny", "cpu", "int8", ("en", "it"), self._reason)

    def warmup(self) -> None:
        self._ready = True

    def transcribe(self, samples: list[float], **kwargs: Any) -> Transcript:
        self.calls.append(len(samples))
        language = kwargs.get("language") or "en"
        return Transcript(f"samples:{len(samples)}", language, "whisper-tiny", 1000)


class BlockingStt(FakeStt):
    def __init__(self) -> None:
        super().__init__()
        self.started = threading.Event()
        self.release = threading.Event()
        self.slots = threading.BoundedSemaphore(1)

    def transcribe(self, samples: list[float], **kwargs: Any) -> Transcript:
        cancel = kwargs.get("cancel")
        if not self.slots.acquire(blocking=False):
            raise RateLimited("too many transcriptions are in progress")
        try:
            self.started.set()
            while not self.release.wait(0.05):
                if cancel is not None and cancel.is_set():
                    raise Cancelled("transcription was cancelled")
            return Transcript("hello", kwargs.get("language") or "en", "whisper-tiny", 1000)
        finally:
            self.slots.release()


class MissingStt(FakeStt):
    def __init__(self) -> None:
        super().__init__(ready=False, available=False, reason="library-missing")

    def transcribe(self, samples: list[float], **kwargs: Any) -> Transcript:
        raise ModelUnavailable("speech model is not installed")


class FakeTts:
    def describe(self) -> TtsStatus:
        return TtsStatus(True, True, ("en_US-lessac-medium",), None)

    def synthesize(self, text: str, **kwargs: Any) -> SynthesizedSpeech:
        return SynthesizedSpeech(wav_bytes([0, 1000, -1000, 0]), kwargs.get("voice") or "en_US-lessac-medium", 16000)


def client_for(app_settings: Settings, stt: Any | None = None, tts: Any | None = None) -> TestClient:
    app = create_app(app_settings)
    if stt is not None:
        app.state.stt = stt
    if tts is not None:
        app.state.tts = tts
    return TestClient(app)


def test_live_is_not_readiness() -> None:
    with client_for(settings(), FakeStt(ready=False, reason="model-not-loaded")) as client:
        live = client.get("/health/live")
        ready = client.get("/health/ready")
    assert live.status_code == 200
    assert live.json()["status"] == "ok"
    assert ready.status_code == 200
    assert ready.json()["ready"] is False
    assert ready.json()["stt"]["reason"] == "model-not-loaded"


def test_ready_true_only_when_engine_is_ready() -> None:
    with client_for(settings(), FakeStt(ready=True)) as client:
        body = client.get("/health/ready").json()
    assert body["ready"] is True
    assert body["stt"]["model"] == "whisper-tiny"
    assert body["realtime"]["ready"] is True
    assert body["realtime"]["vad"] == "energy"


def test_transcription_requires_authentication() -> None:
    with client_for(settings(), FakeStt()) as client:
        missing = client.post("/v1/audio/transcriptions", files={"file": ("a.wav", loud_wav(), "audio/wav")})
        wrong = client.post(
            "/v1/audio/transcriptions",
            headers=auth("not-the-right-key"),
            files={"file": ("a.wav", loud_wav(), "audio/wav")},
        )
    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "unauthenticated"
    assert wrong.status_code == 401


def test_production_rejects_development_token() -> None:
    app_settings = settings(environment="production", auth_mode="token", api_key="development-token")
    with client_for(app_settings, FakeStt()) as client:
        response = client.post(
            "/v1/audio/transcriptions",
            headers={"Authorization": "Bearer development-token"},
            files={"file": ("a.wav", loud_wav(), "audio/wav")},
        )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


def test_transcription_schema_and_silence() -> None:
    engine = FakeStt()
    with client_for(settings(), engine) as client:
        response = client.post(
            "/v1/audio/transcriptions",
            headers=auth(),
            data={"language": "en", "model": "tiny", "request_id": "utt_123"},
            files={"file": ("silence.wav", wav_bytes([0] * 1600), "audio/wav")},
        )
    body = response.json()
    assert response.status_code == 200
    assert body["text"] == ""
    assert body["language"] == "en"
    assert body["model"] == "whisper-tiny"
    assert body["is_final"] is True
    assert body["request_id"] == "utt_123"
    assert body["duration_ms"] > 0
    assert engine.calls == []
    assert response.headers["cache-control"] == "no-store"


def test_loud_audio_reaches_engine_once() -> None:
    engine = FakeStt()
    payload = loud_wav()
    with client_for(settings(), engine) as client:
        first = client.post(
            "/v1/audio/transcriptions",
            headers=auth(),
            data={"language": "it"},
            files={"file": ("tone.wav", payload, "audio/wav")},
        )
        second = client.post(
            "/v1/audio/transcriptions",
            headers=auth(),
            files={"audio": ("tone.wav", payload, "audio/wav")},
        )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["text"].startswith("samples:")
    assert first.json()["language"] == "it"
    assert first.json()["text"] != second.json()["request_id"]
    assert len(engine.calls) == 2


def test_invalid_truncated_and_unsupported_audio() -> None:
    with client_for(settings(), FakeStt()) as client:
        empty = client.post(
            "/v1/audio/transcriptions",
            headers=auth(),
            files={"file": ("empty.wav", b"", "audio/wav")},
        )
        truncated = client.post(
            "/v1/audio/transcriptions",
            headers=auth(),
            files={"file": ("bad.wav", b"RIFF----WAVE", "audio/wav")},
        )
        unsupported = client.post(
            "/v1/audio/transcriptions",
            headers=auth(),
            files={"file": ("notes.txt", b"this is not audio", "text/plain")},
        )
        language = client.post(
            "/v1/audio/transcriptions",
            headers=auth(),
            data={"language": "ja"},
            files={"file": ("a.wav", loud_wav(), "audio/wav")},
        )
        model = client.post(
            "/v1/audio/transcriptions",
            headers=auth(),
            data={"model": "tiny.en"},
            files={"file": ("a.wav", loud_wav(), "audio/wav")},
        )
    assert empty.status_code == 422
    assert empty.json()["error"]["code"] == "invalid_audio"
    assert truncated.status_code == 422
    assert truncated.json()["error"]["code"] == "invalid_audio"
    assert unsupported.status_code == 415
    assert unsupported.json()["error"]["code"] == "unsupported_codec"
    assert language.status_code == 400
    assert language.json()["error"]["code"] == "unsupported_language"
    assert model.status_code == 400
    assert model.json()["error"]["code"] == "unsupported_model"


def test_oversized_and_too_long_audio() -> None:
    with client_for(settings(max_upload_bytes=40), FakeStt()) as client:
        oversized = client.post(
            "/v1/audio/transcriptions",
            headers=auth(),
            files={"file": ("big.wav", wav_bytes([0] * 80), "audio/wav")},
        )
    with client_for(settings(max_audio_seconds=0.2), FakeStt()) as client:
        too_long = client.post(
            "/v1/audio/transcriptions",
            headers=auth(),
            files={"file": ("long.wav", wav_bytes([0] * 8000), "audio/wav")},
        )
    assert oversized.status_code == 413
    assert oversized.json()["error"]["code"] == "audio_too_large"
    assert too_long.status_code == 413
    assert too_long.json()["error"]["code"] == "audio_too_long"


def test_content_length_is_rejected_before_inference() -> None:
    engine = FakeStt()
    blob = b"x" * 80_000
    with client_for(settings(max_upload_bytes=100), engine) as client:
        response = client.post(
            "/v1/audio/transcriptions",
            headers={**auth(), "content-length": str(len(blob))},
            content=blob,
        )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "audio_too_large"
    assert engine.calls == []


def test_missing_model_and_capabilities() -> None:
    with client_for(settings(), MissingStt()) as client:
        caps = client.get("/v1/audio/capabilities", headers=auth())
        speech = client.post(
            "/v1/audio/transcriptions",
            headers=auth(),
            files={"file": ("a.wav", loud_wav(), "audio/wav")},
        )
        anonymous = client.get("/v1/audio/capabilities")
    assert anonymous.status_code == 401
    assert caps.status_code == 200
    assert caps.json()["stt"]["available"] is False
    assert caps.json()["stt"]["ready"] is False
    assert caps.json()["tts"]["available"] is False
    assert caps.json()["realtime"]["available"] is True
    assert caps.json()["realtime"]["ready"] is False
    assert caps.json()["realtime"]["reason"] == "library-missing"
    assert "device_id" not in caps.json()["route"]
    assert speech.status_code == 503
    assert speech.json()["error"]["code"] == "model_unavailable"


def test_concurrency_limit_and_timeout() -> None:
    import asyncio

    import httpx

    blocking = BlockingStt()
    app = create_app(settings(stt_timeout_sec=2))
    app.state.stt = blocking

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

            async def post(request_id: str) -> httpx.Response:
                return await client.post(
                    "/v1/audio/transcriptions",
                    headers=auth(),
                    data={"request_id": request_id},
                    files={"file": ("a.wav", loud_wav(), "audio/wav")},
                )

            first_task = asyncio.create_task(post("utt_hold"))
            for _ in range(40):
                if blocking.started.is_set():
                    break
                await asyncio.sleep(0.05)
            assert blocking.started.is_set()
            limited = await post("utt_second")
            duplicate = await post("utt_hold")
            assert limited.status_code == 429
            assert limited.json()["error"]["code"] == "rate_limited"
            assert duplicate.status_code == 409
            assert duplicate.json()["error"]["code"] == "duplicate_request"
            blocking.release.set()
            first = await first_task
            assert first.status_code == 200

    asyncio.run(scenario())
    timeout_engine = BlockingStt()
    with client_for(settings(stt_timeout_sec=0.3), timeout_engine) as client:
        timed = client.post(
            "/v1/audio/transcriptions",
            headers=auth(),
            data={"request_id": "utt_timeout"},
            files={"file": ("a.wav", loud_wav(), "audio/wav")},
        )
    assert timed.status_code == 504
    assert timed.json()["error"]["code"] == "timeout"
    timeout_engine.release.set()


def test_origin_allowlist_and_voice_flag() -> None:
    with client_for(settings(allowed_origins="https://avatar.example"), FakeStt()) as client:
        denied = client.post(
            "/v1/audio/transcriptions",
            headers={**auth(), "Origin": "https://evil.example"},
            files={"file": ("a.wav", loud_wav(), "audio/wav")},
        )
        allowed = client.post(
            "/v1/audio/transcriptions",
            headers={**auth(), "Origin": "https://avatar.example"},
            files={"file": ("a.wav", wav_bytes([0] * 800), "audio/wav")},
        )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "origin_denied"
    assert allowed.status_code == 200
    with client_for(settings(voice_enabled=False), FakeStt()) as client:
        disabled = client.get("/v1/audio/capabilities", headers=auth())
        ready = client.get("/health/ready")
    assert disabled.status_code == 404
    assert ready.json()["ready"] is False
    assert ready.json()["stt"]["reason"] == "voice-disabled"


def test_metrics_do_not_include_transcript_text(caplog: Any) -> None:
    engine = FakeStt()
    with client_for(settings(), engine) as client:
        response = client.post(
            "/v1/audio/transcriptions",
            headers=auth(),
            files={"file": ("a.wav", loud_wav(), "audio/wav")},
        )
        metrics = client.get("/metrics")
    text = response.json()["text"]
    assert text.startswith("samples:")
    assert text not in metrics.text
    assert "sonicagent_stt_requests_total" in metrics.text
    assert text not in caplog.text


def test_optional_tts_failure_and_fake_success() -> None:
    with client_for(settings(tts_enabled=False), FakeStt()) as client:
        missing = client.post(
            "/v1/audio/speech",
            headers=auth(),
            json={"text": "Hello", "voice": "en_US-lessac-medium", "format": "wav"},
        )
    assert missing.status_code == 503
    assert missing.json()["error"]["code"] == "voice_unavailable"
    with client_for(settings(tts_enabled=True), FakeStt(), FakeTts()) as client:
        spoken = client.post(
            "/v1/audio/speech",
            headers=auth(),
            json={"text": "Hello", "voice": "en_US-lessac-medium", "language": "en", "format": "wav"},
        )
        bad_format = client.post(
            "/v1/audio/speech",
            headers=auth(),
            json={"text": "Hello", "format": "mp3"},
        )
    assert spoken.status_code == 200
    assert spoken.headers["content-type"].startswith("audio/wav")
    assert spoken.content.startswith(b"RIFF")
    assert bad_format.status_code == 400
    assert bad_format.json()["error"]["code"] == "unsupported_format"


def test_warmup_does_not_block_liveness() -> None:
    class SlowWarm(FakeStt):
        def __init__(self) -> None:
            super().__init__(ready=False, reason="model-not-loaded")
            self.started = threading.Event()

        def warmup(self) -> None:
            self.started.set()
            time.sleep(0.8)
            self._ready = True
            self._reason = None

    engine = SlowWarm()
    app = create_app(settings(stt_warmup=True))
    app.state.stt = engine
    started = time.perf_counter()
    with TestClient(app) as client:
        live = client.get("/health/live")
        elapsed = time.perf_counter() - started
    assert live.status_code == 200
    assert elapsed < 0.7
    assert engine.started.wait(1)
