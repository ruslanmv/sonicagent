"""Speech-only streaming. These turns never call the language model."""

from __future__ import annotations

import json
import threading

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from sonicagent_rt.api.app_factory import create_app
from sonicagent_rt.audio.pcm import floats_to_pcm16
from sonicagent_rt.stt.errors import Cancelled
from sonicagent_rt.tts.base import TtsStatus
from tests.unit.test_realtime_session import _frame
from tests.unit.test_voice_api import DEV_KEY, BlockingStt, FakeStt, FakeTts, auth, client_for, settings


class ExplodingLlm:
    def __init__(self) -> None:
        self.calls = 0

    def __getattr__(self, name: str):
        self.calls += 1
        raise AssertionError(name)


class GatedTts:
    """Yields the first sentence, then waits. The second sentence is not synthesized early."""

    def __init__(self) -> None:
        self.release = threading.Event()

    def describe(self) -> TtsStatus:
        return TtsStatus(True, True, ("en_US-lessac-medium",), None)

    def iter_pcm(self, text: str, *, voice: str, language: str | None, cancel: object):
        del text, voice, language
        yield 16000, floats_to_pcm16([0.25] * 320)
        while not self.release.wait(0.05):
            if cancel is not None and getattr(cancel, "is_set", lambda: False)():
                raise Cancelled("synthesis was cancelled")
        yield 16000, floats_to_pcm16([-0.25] * 320)


def _speech_settings(**overrides: object):
    base = dict(vad_min_speech_ms=20, vad_min_silence_ms=20, vad_threshold=0.2)
    base.update(overrides)
    return settings(**base)


def _create(client: TestClient, **body: object):
    payload = {"mode": "stt_only", "language": "en", "voice_id": "en_US-lessac-medium"}
    payload.update(body)
    return client.post("/v1/audio/stream-sessions", headers=auth(), json=payload)


def _url(created: dict[str, object]) -> str:
    return f"/v1/audio/stream/{created['session_id']}?resume_token={created['resume_token']}"


def _collect(socket: object, limit: int = 24, stop: set[str] | None = None) -> tuple[list[dict], int]:
    names = stop or {"metrics.turn", "turn.cancelled", "session.closed"}
    events: list[dict] = []
    frames = 0
    for _ in range(limit):
        message = socket.receive()
        if message.get("bytes") is not None:
            frames += 1
            continue
        event = json.loads(message["text"])
        events.append(event)
        if event.get("type") in names:
            break
    return events, frames


def test_stream_session_hides_the_service_credential() -> None:
    with client_for(_speech_settings(), FakeStt()) as client:
        denied = client.post("/v1/audio/stream-sessions", json={"mode": "stt_only"})
        moonshine = client.post(
            "/v1/audio/stream-sessions",
            headers=auth(),
            json={"mode": "stt_only", "stt_provider": "moonshine-streaming"},
        )
        rejected = client.post(
            "/v1/audio/stream-sessions",
            headers=auth(),
            json={"mode": "chat", "stt_provider": "faster-whisper"},
        )
        created = _create(client, language="it", voice_id="it_IT-paola-medium")
    assert denied.status_code == 401
    assert moonshine.status_code == 400
    assert "not installed" in moonshine.json()["error"]["message"]
    assert rejected.status_code == 400
    body = created.json()
    assert created.status_code == 200
    assert body["protocol"] == "sonic-speech-stream-v1"
    assert body["llm"] is False
    assert body["stt"]["streaming_mode"] == "endpointed"
    assert body["stt"]["partial_results"] is False
    assert body["tts"]["incremental"] == "sentence"
    assert body["resume_token"] != DEV_KEY
    assert DEV_KEY not in body["websocket_url"]
    assert body["websocket_url"] == f"/v1/audio/stream/{body['session_id']}"


def test_capabilities_keep_the_batch_fields_and_report_uninstalled_stream_engines() -> None:
    with client_for(_speech_settings(), FakeStt()) as client:
        body = client.get("/v1/audio/capabilities", headers=auth()).json()
    assert body["stt"]["mode"] == "batch"
    assert body["realtime"]["available"] is True
    assert body["route"] == {"location": "sonicagent"}
    assert body["streaming"]["protocol"] == "sonic-speech-stream-v1"
    assert body["streaming"]["partial_results"] is False
    assert body["streaming"]["llm"] is False
    assert body["streaming"]["modes"] == ["stt_only", "tts_only", "duplex_speech"]
    providers = {item["id"]: item for item in body["stt_providers"]}
    assert providers["faster-whisper"]["streaming_mode"] == "endpointed"
    assert providers["faster-whisper"]["partial_results"] is False
    assert providers["faster-whisper"]["ready"] is True
    assert "it" in providers["faster-whisper"]["languages"]
    assert providers["moonshine-streaming"]["ready"] is False
    assert providers["moonshine-streaming"]["languages"] == ["en"]
    assert providers["nemotron-stream"]["ready"] is False
    voices = {item["id"]: item for item in body["tts_providers"]}
    assert voices["piper"]["incremental"] == "sentence"
    assert voices["pocket-tts-stream"]["ready"] is False


def test_stt_only_emits_one_final_transcript_and_does_not_call_the_language_model() -> None:
    llm = ExplodingLlm()
    app = create_app(_speech_settings())
    app.state.stt = FakeStt()
    app.state.llm = llm
    with TestClient(app) as client:
        created = _create(client, mode="stt_only", language="it").json()
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(
                f"/v1/realtime/{created['session_id']}?resume_token={created['resume_token']}"
            ) as realtime:
                realtime.receive_text()
        with client.websocket_connect(_url(created)) as socket:
            hello = socket.receive_json()
            socket.send_bytes(_frame([0.8] * 320, 0, end=True))
            events, _frames = _collect(socket)
            socket.send_text(json.dumps({"type": "tts.speak", "text": "Ciao."}))
            refused, _frames = _collect(socket, stop={"session.error"})
    assert hello["type"] == "session.ready"
    assert hello["llm"] is False
    assert hello["partial_results"] is False
    finals = [event for event in events if event["type"] == "transcript.final"]
    assert len(finals) == 1
    assert finals[0]["language"] == "it"
    assert finals[0]["is_final"] is True
    assert all(event["type"] != "transcript.partial" for event in events)
    metrics = [event for event in events if event["type"] == "metrics.turn"]
    assert metrics[-1]["llm"] is False
    assert metrics[-1]["partials"] == 0
    assert refused[0]["type"] == "session.error"
    assert refused[0]["message"] == "this session does not speak"
    assert llm.calls == 0


def test_tts_only_speaks_the_first_sentence_before_the_rest_and_rejects_audio() -> None:
    engine = GatedTts()
    app = create_app(_speech_settings())
    app.state.stt = FakeStt()
    app.state.tts = engine
    with TestClient(app) as client:
        created = _create(client, mode="tts_only").json()
        with client.websocket_connect(_url(created)) as socket:
            socket.receive_json()
            socket.send_bytes(_frame([0.8] * 320, 0, end=True))
            rejected, _frames = _collect(socket, stop={"session.error"})
            socket.send_text(json.dumps({"type": "tts.speak", "text": "Hello. How are you?"}))
            first, early_frames = _collect(socket, stop={"tts.audio.chunk"})
            assert all(event["type"] != "tts.audio.done" for event in first)
            assert engine.release.is_set() is False
            engine.release.set()
            rest, later_frames = _collect(socket)
    assert rejected[0]["message"] == "this session does not accept audio"
    assert any(event["type"] == "tts.audio.meta" and event["incremental"] == "sentence" for event in first)
    done = [event for event in rest if event["type"] == "tts.audio.done"]
    metrics = [event for event in rest if event["type"] == "metrics.turn"]
    assert done[0]["frames"] == 2
    assert early_frames + later_frames == 2
    assert metrics[0]["llm"] is False
    assert metrics[0]["tts_first_ms"] is not None


def test_cancel_stops_synthesis_before_the_second_sentence() -> None:
    engine = GatedTts()
    app = create_app(_speech_settings())
    app.state.tts = engine
    with TestClient(app) as client:
        created = _create(client, mode="tts_only").json()
        with client.websocket_connect(_url(created)) as socket:
            socket.receive_json()
            socket.send_text(json.dumps({"type": "tts.speak", "text": "Hello. Stay.", "turn_id": "turn_stop"}))
            _collect(socket, stop={"tts.audio.chunk"})
            socket.send_text(json.dumps({"type": "turn.cancel", "turn_id": "turn_stop"}))
            events, _frames = _collect(socket)
    assert any(event["type"] == "turn.cancelled" and event["clear_audio"] is True for event in events)
    assert all(event["type"] != "tts.audio.done" for event in events)


def test_cancel_during_transcription_does_not_emit_a_final() -> None:
    engine = BlockingStt()
    app = create_app(_speech_settings())
    app.state.stt = engine
    with TestClient(app) as client:
        created = _create(client, mode="stt_only").json()
        with client.websocket_connect(_url(created)) as socket:
            socket.receive_json()
            socket.send_bytes(_frame([0.8] * 320, 0, end=True))
            assert engine.started.wait(2)
            socket.send_text(json.dumps({"type": "turn.cancel", "turn_id": "turn_cut"}))
            events, _frames = _collect(socket, limit=12)
    engine.release.set()
    assert any(event["type"] == "turn.cancelled" for event in events)
    assert all(event["type"] != "transcript.final" for event in events)


def test_a_second_socket_is_refused_until_the_first_disconnects() -> None:
    with client_for(_speech_settings(), FakeStt(), FakeTts()) as client:
        created = _create(client).json()
        url = _url(created)
        with client.websocket_connect(url) as first:
            assert first.receive_json()["type"] == "session.ready"
            with pytest.raises(WebSocketDisconnect) as caught:
                with client.websocket_connect(url) as second:
                    second.receive_text()
            assert caught.value.code == 1008
            first.send_text(json.dumps({"type": "ping"}))
            assert first.receive_json()["type"] == "pong"
        with client.websocket_connect(url) as resumed:
            assert resumed.receive_json()["type"] == "session.ready"


def test_a_skipped_sequence_is_rejected() -> None:
    with client_for(_speech_settings(), FakeStt()) as client:
        created = _create(client).json()
        with client.websocket_connect(_url(created)) as socket:
            socket.receive_json()
            socket.send_bytes(_frame([0.0] * 320, 0))
            started, _frames = _collect(socket, stop={"audio.input.started"})
            socket.send_bytes(_frame([0.0] * 320, 2))
            failed, _frames = _collect(socket, stop={"session.error"})
    assert started[0]["type"] == "audio.input.started"
    assert failed[0]["code"] == "invalid_audio"


def test_outbound_audio_is_bounded() -> None:
    with client_for(_speech_settings(max_outbound_queue_ms=0), FakeStt(), FakeTts()) as client:
        created = _create(client, mode="tts_only").json()
        with client.websocket_connect(_url(created)) as socket:
            socket.receive_json()
            socket.send_text(json.dumps({"type": "tts.speak", "text": "Hello."}))
            events, frames = _collect(socket, stop={"session.error", "metrics.turn"})
    assert frames == 0
    assert events[-1]["code"] == "rate_limited"
    assert all(event["type"] != "tts.audio.done" for event in events)


def test_sentence_chunks_stay_separate_from_a_finished_wav() -> None:
    from sonicagent_rt.speech_stream.chunks import iter_pcm16, split_frames

    class OnlyChunks:
        def iter_pcm(self, text: str, *, voice: str, language: str | None, cancel: object):
            del text, voice, language, cancel
            yield 22050, b"\x01\x00"
            yield 22050, b"\x02\x00"

        def synthesize(self, text: str, **kwargs: object) -> object:
            del text, kwargs
            raise AssertionError("full wav")

    chunks = list(
        iter_pcm16(OnlyChunks(), "Hi.", voice="en_US-lessac-medium", language="en", cancel=threading.Event())
    )
    assert chunks == [(22050, b"\x01\x00"), (22050, b"\x02\x00")]
    pieces = list(split_frames(b"\x00\x01" * 400, 16000, 20))
    assert b"".join(pieces) == b"\x00\x01" * 400
    assert len(pieces) == 2
