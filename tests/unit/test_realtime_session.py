"""Realtime session, endpointing, and one mocked turn."""

from __future__ import annotations

import json

import pytest
from starlette.websockets import WebSocketDisconnect

from sonicagent_rt.audio.pcm import floats_to_pcm16
from sonicagent_rt.protocol.binary_frame import BinaryAudioFrame
from sonicagent_rt.protocol.constants import Codec, FLAG_END_OF_UTTERANCE, MessageType
from sonicagent_rt.vad.energy_fallback import EnergyEndpoint
from tests.unit.test_voice_api import DEV_KEY, BlockingStt, FakeStt, FakeTts, auth, client_for, settings


def _frame(samples: list[float], sequence: int, *, end: bool = False) -> bytes:
    return BinaryAudioFrame(
        message_type=int(MessageType.AUDIO_INPUT),
        codec=int(Codec.PCM16),
        flags=FLAG_END_OF_UTTERANCE if end else 0,
        sample_rate=16000,
        sequence=sequence,
        timestamp_us=sequence * 20_000,
        payload=floats_to_pcm16(samples),
    ).encode()


def test_energy_endpoint_opens_and_closes() -> None:
    detector = EnergyEndpoint(
        threshold=0.2,
        min_speech_ms=20,
        min_silence_ms=20,
        pre_roll_ms=0,
        max_utterance_sec=2,
        sample_rate=16000,
    )
    loud = [0.8] * 320
    quiet = [0.0] * 320
    assert [event.kind for event in detector.push(loud)] == ["started"]
    finished = detector.push(quiet)
    assert [event.kind for event in finished] == ["utterance"]
    assert len(finished[0].samples) > 320


def test_session_token_is_required_and_not_the_development_placeholder() -> None:
    app_settings = settings(vad_min_speech_ms=20, vad_min_silence_ms=20, vad_threshold=0.2)
    with client_for(app_settings, FakeStt()) as client:
        denied = client.post("/v1/sessions", json={"language": "en", "voice_id": "en_US-lessac-medium"})
        created = client.post(
            "/v1/sessions",
            headers=auth(),
            json={"language": "en", "voice_id": "en_US-lessac-medium"},
        )
        assert denied.status_code == 401
        body = created.json()
        assert created.status_code == 200
        assert body["resume_token"] != "development-token"
        assert len(body["resume_token"]) >= 32
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(f"/v1/realtime/{body['session_id']}") as socket:
                socket.receive_text()


def test_turn_returns_a_transcript_without_logging_the_token() -> None:
    with client_for(settings(vad_min_speech_ms=20, vad_min_silence_ms=20, vad_threshold=0.2), FakeStt()) as client:
        created = client.post(
            "/v1/sessions",
            headers={"Authorization": f"Bearer {DEV_KEY}"},
            json={"language": "it", "voice_id": "it_IT-paola-medium"},
        ).json()
        with client.websocket_connect(
            f"/v1/realtime/{created['session_id']}?resume_token={created['resume_token']}"
        ) as socket:
            hello = socket.receive_json()
            socket.send_text(json.dumps({"type": "ping"}))
            pong = socket.receive_json()
            socket.send_bytes(_frame([0.8] * 320, 0, end=True))
            events = []
            for _ in range(16):
                event = socket.receive_json()
                events.append(event)
                if event.get("type") == "metrics.turn":
                    break
    assert hello["type"] == "session.created"
    assert hello["status"] == "ready"
    assert pong == {"type": "pong"}
    kinds = [event["type"] for event in events]
    assert "transcript.final" in kinds
    assert "metrics.turn" in kinds
    assert all("resume_token" not in event for event in events)


def test_barge_in_cancels_the_active_turn() -> None:
    engine = BlockingStt()
    app_settings = settings(vad_min_speech_ms=20, vad_min_silence_ms=20, vad_threshold=0.2, barge_in_enabled=True)
    with client_for(app_settings, engine, FakeTts()) as client:
        created = client.post(
            "/v1/sessions",
            headers=auth(),
            json={"language": "en", "voice_id": "en_US-lessac-medium"},
        ).json()
        with client.websocket_connect(
            f"/v1/realtime/{created['session_id']}?resume_token={created['resume_token']}"
        ) as socket:
            socket.receive_json()
            socket.send_bytes(_frame([0.8] * 320, 0, end=True))
            assert engine.started.wait(2)
            socket.send_bytes(_frame([0.9] * 320, 1))
            seen = []
            for _ in range(12):
                message = socket.receive()
                if "text" in message:
                    seen.append(json.loads(message["text"])["type"])
                if "response.cancelled" in seen:
                    break
    assert "response.cancelled" in seen
    engine.release.set()
