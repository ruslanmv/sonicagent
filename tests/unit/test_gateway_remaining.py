"""Reconnect, phrase playback, noisy-room endpointing, and LLM retry."""

from __future__ import annotations

import asyncio
import io
import json
import threading
import time
import wave

import pytest
from starlette.websockets import WebSocketDisconnect

from sonicagent_rt.llm.openai_compatible import OpenAICompatibleLLM
from sonicagent_rt.pipeline.cancellation import CancellationToken
from sonicagent_rt.pipeline.orchestrator import run_turn
from sonicagent_rt.sessions.memory_store import MemorySessionStore
from sonicagent_rt.sessions.models import SpeechSession
from sonicagent_rt.stt.base import Transcript
from sonicagent_rt.stt.errors import RateLimited
from sonicagent_rt.tts.base import SynthesizedSpeech, TtsStatus
from sonicagent_rt.vad.energy_fallback import EnergyEndpoint
from sonicagent_rt.vad.silero_onnx import SILERO_VAD_SHA256, silero_available
from tests.unit.test_realtime_session import _frame
from tests.unit.test_voice_api import DEV_KEY, FakeStt, auth, client_for, settings


def _wav() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x10" * 320)
    return buffer.getvalue()


def test_noise_does_not_open_and_preroll_is_kept() -> None:
    detector = EnergyEndpoint(
        threshold=0.2,
        min_speech_ms=20,
        min_silence_ms=20,
        pre_roll_ms=20,
        max_utterance_sec=2,
        sample_rate=16000,
    )
    assert detector.push([0.02] * 320) == []
    assert [event.kind for event in detector.push([0.8] * 320)] == ["started"]
    finished = detector.push([0.02] * 320)
    assert finished[0].kind == "utterance"
    assert len(finished[0].samples) >= 640


def test_silero_file_must_match_the_pin() -> None:
    assert len(SILERO_VAD_SHA256) == 64
    assert silero_available("") is False
    assert silero_available("/tmp/does-not-exist-silero.onnx") is False


def test_first_phrase_is_spoken_before_the_reply_finishes() -> None:
    order: list[str] = []

    class Script:
        async def stream(self, messages: list[object], cancellation: object | None = None):
            order.append("first")
            yield "Hello. "
            order.append("second")
            yield "Stay with me."

    class Speech:
        def describe(self) -> TtsStatus:
            return TtsStatus(True, True, ("en_US-lessac-medium",), None)

        def synthesize(self, text: str, **kwargs: object) -> SynthesizedSpeech:
            order.append(f"audio:{text}")
            return SynthesizedSpeech(_wav(), "en_US-lessac-medium", 16000)

    class Ear:
        def transcribe(self, samples: list[float], **kwargs: object) -> Transcript:
            return Transcript("hi", "en", "whisper-tiny", 20)

    async def collect() -> list[str]:
        kinds: list[str] = []
        async for item in run_turn(
            samples=[0.1] * 320,
            sample_rate=16000,
            language="en",
            voice_id="en_US-lessac-medium",
            stt=Ear(),
            llm=Script(),
            tts=Speech(),
            settings=settings(tts_phrase_max_chars=180),
            cancellation=CancellationToken(),
            turn_id="turn_phrase",
            speech_ms=20,
        ):
            if isinstance(item, dict):
                kinds.append(str(item["type"]))
        return kinds

    kinds = asyncio.run(collect())
    assert order.index("audio:Hello.") < order.index("second")
    assert "response.audio.started" in kinds
    assert "metrics.turn" in kinds


def test_llm_retries_once_and_does_not_log_the_prompt(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    calls = {"n": 0}

    class Body:
        def __iter__(self):
            yield b'data: {"choices":[{"delta":{"content":"Hi"}}]}\n'
            yield b"data: [DONE]\n"

        def __enter__(self) -> Body:
            return self

        def __exit__(self, *args: object) -> bool:
            return False

    def fake_urlopen(request: object, timeout: float) -> Body:
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError("slow")
        assert timeout == 5
        return Body()

    monkeypatch.setattr("sonicagent_rt.llm.openai_compatible.urlopen", fake_urlopen)
    client = OpenAICompatibleLLM(
        base_url="http://llm.test/v1",
        api_key="",
        model="local",
        temperature=0,
        max_tokens=8,
        timeout_sec=5,
    )

    async def read() -> str:
        parts = [part async for part in client.stream([{"role": "user", "content": "secret phrase"}])]
        return "".join(parts)

    with caplog.at_level("INFO"):
        assert asyncio.run(read()) == "Hi"
    assert calls["n"] == 2
    assert "secret phrase" not in caplog.text


def test_reconnect_is_allowed_and_a_second_live_socket_is_rejected() -> None:
    app_settings = settings(vad_min_speech_ms=20, vad_min_silence_ms=20, vad_threshold=0.2, stt_rate_limit_per_minute=10)
    with client_for(app_settings, FakeStt()) as client:
        created = client.post(
            "/v1/sessions",
            headers={"Authorization": f"Bearer {DEV_KEY}"},
            json={"language": "en", "voice_id": "en_US-lessac-medium"},
        ).json()
        url = f"/v1/realtime/{created['session_id']}?resume_token={created['resume_token']}"
        with client.websocket_connect(url) as first:
            assert first.receive_json()["resumed"] is False
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect(url) as second:
                    second.receive_text()
        with client.websocket_connect(url) as again:
            resumed = again.receive_json()
            again.send_bytes(_frame([0.8] * 320, 0, end=True))
    assert resumed["type"] == "session.updated"
    assert resumed["resumed"] is True


def test_session_create_is_rate_limited() -> None:
    with client_for(settings(stt_rate_limit_per_minute=1), FakeStt()) as client:
        first = client.post("/v1/sessions", headers=auth(), json={"language": "en", "voice_id": "en_US-lessac-medium"})
        second = client.post("/v1/sessions", headers=auth(), json={"language": "en", "voice_id": "en_US-lessac-medium"})
    assert first.status_code == 200
    assert second.status_code == 429
    assert "secret" not in json.dumps(second.json())


def test_one_live_holder_under_concurrent_acquire() -> None:
    store = MemorySessionStore(ttl_sec=30, max_sessions=8)
    session = SpeechSession(
        session_id="ses_load",
        resume_token="resume-token",
        language="en",
        voice_id="en_US-lessac-medium",
        expires_at=time.monotonic() + 30,
    )
    store.put(session)
    results: list[str] = []
    lock = threading.Lock()

    def grab() -> None:
        try:
            store.acquire(session.session_id, session.resume_token)
            outcome = "ok"
        except RateLimited:
            outcome = "busy"
        with lock:
            results.append(outcome)

    workers = [threading.Thread(target=grab) for _ in range(8)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    assert results.count("ok") == 1
    assert results.count("busy") == 7
