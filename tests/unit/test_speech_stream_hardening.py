"""HV3 hardening of the speech-only socket.

Each test names the failure it keeps from coming back. The v1 behaviour of a
client that negotiates nothing is covered by ``test_speech_stream.py``, which
this change leaves untouched.
"""

from __future__ import annotations

import json
import threading
import time

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from sonicagent_rt.api.app_factory import create_app
from sonicagent_rt.audio.pcm import floats_to_pcm16
from sonicagent_rt.protocol.binary_frame import BinaryAudioFrame, decode_frame
from sonicagent_rt.protocol.constants import FLAG_END_OF_UTTERANCE, Codec, MessageType
from sonicagent_rt.speech_stream.store import SpeechStreamSession, SpeechStreamStore, StreamOptions
from sonicagent_rt.stt.errors import InvalidRequest, RateLimited, Unauthenticated
from sonicagent_rt.tts.base import TtsStatus
from tests.unit.test_speech_stream import GatedTts, _collect, _create, _speech_settings, _url
from tests.unit.test_voice_api import BlockingStt, FakeStt, client_for


def _frame(
    samples: list[float], sequence: int, *, end: bool = False, rate: int = 16000, raw: bytes | None = None
):
    return BinaryAudioFrame(
        message_type=int(MessageType.AUDIO_INPUT),
        codec=int(Codec.PCM16),
        flags=FLAG_END_OF_UTTERANCE if end else 0,
        sample_rate=rate,
        sequence=sequence,
        timestamp_us=sequence * 20_000,
        payload=raw if raw is not None else floats_to_pcm16(samples),
    ).encode()


class LongTts:
    """One sentence of ``seconds`` of audio at 16 kHz."""

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds

    def describe(self) -> TtsStatus:
        return TtsStatus(True, True, ("en_US-lessac-medium",), None)

    def iter_pcm(self, text: str, *, voice: str, language: str | None, cancel: object):
        del text, voice, language, cancel
        yield 16000, floats_to_pcm16([0.1] * int(16000 * self.seconds))


def _app(**overrides: object):
    app = create_app(_speech_settings(**overrides))
    app.state.stt = FakeStt()
    return app


# ── Backpressure ─────────────────────────────────────────────────────


def test_a_reply_longer_than_the_queue_limit_is_paced_not_cut() -> None:
    # v1 counted every frame ever sent against the limit, so a reply longer
    # than SONIC_MAX_OUTBOUND_QUEUE_MS (default 2000 ms) always ended in
    # "outbound audio queue is full". Here the limit is 100 ms and the reply
    # 600 ms: all of it arrives, at roughly real time after the first 100 ms.
    app = _app(max_outbound_queue_ms=100)
    app.state.tts = LongTts(0.6)
    with TestClient(app) as client:
        created = _create(client, mode="tts_only").json()
        with client.websocket_connect(_url(created)) as socket:
            socket.receive_json()
            started = time.monotonic()
            socket.send_text(json.dumps({"type": "tts.speak", "text": "Long."}))
            events, frames = _collect(socket, limit=200)
            elapsed = time.monotonic() - started
    assert all(event.get("code") != "rate_limited" for event in events)
    done = [event for event in events if event["type"] == "tts.audio.done"]
    assert done and done[0]["frames"] == 30 and frames == 30
    assert done[0]["audio_ms"] == 600
    # Paced: it cannot have outrun playback by more than the limit.
    assert elapsed >= 0.6 - 0.1 - 0.15


def test_ack_flow_control_waits_for_playback_then_finishes() -> None:
    app = _app(max_outbound_queue_ms=100)
    app.state.tts = LongTts(0.4)
    with TestClient(app) as client:
        created = _create(client, mode="tts_only", stream_options={"flow_control": "ack"}).json()
        assert created["options"]["flow_control"] == "ack"
        with client.websocket_connect(_url(created)) as socket:
            socket.receive_json()
            socket.send_text(json.dumps({"type": "tts.speak", "text": "Ack.", "turn_id": "t1"}))
            frames = 0
            while frames < 5:  # 100 ms of 20 ms frames: everything the budget allows
                message = socket.receive()
                if message.get("bytes") is not None:
                    frames += 1
            socket.send_text(json.dumps({"type": "playback.ack", "turn_id": "t1", "played_ms": 400}))
            events, more = _collect(socket, limit=200)
    assert frames + more == 20
    assert any(event["type"] == "tts.audio.done" for event in events)


def test_a_zero_queue_still_refuses_as_v1_did() -> None:
    with client_for(_speech_settings(max_outbound_queue_ms=0), FakeStt(), LongTts(0.1)) as client:
        created = _create(client, mode="tts_only").json()
        with client.websocket_connect(_url(created)) as socket:
            socket.receive_json()
            socket.send_text(json.dumps({"type": "tts.speak", "text": "Hi."}))
            events, frames = _collect(socket, stop={"session.error", "metrics.turn"})
    assert frames == 0 and events[-1]["code"] == "rate_limited"


# ── Fewer messages per second of speech ──────────────────────────────


def test_negotiated_40ms_frames_without_chunk_events() -> None:
    app = _app()
    app.state.tts = LongTts(0.2)
    with TestClient(app) as client:
        created = _create(
            client, mode="tts_only", stream_options={"chunk_events": "none", "output_frame_ms": 40}
        ).json()
        with client.websocket_connect(_url(created)) as socket:
            hello = socket.receive_json()
            socket.send_text(json.dumps({"type": "tts.speak", "text": "Short.", "turn_id": "t2"}))
            events: list[dict] = []
            payloads: list[bytes] = []
            while True:
                message = socket.receive()
                if message.get("bytes") is not None:
                    payloads.append(message["bytes"])
                    continue
                event = json.loads(message["text"])
                events.append(event)
                if event["type"] == "metrics.turn":
                    break
    assert hello["options"]["chunk_events"] == "none"
    assert all(event["type"] != "tts.audio.chunk" for event in events)
    meta = next(event for event in events if event["type"] == "tts.audio.meta")
    assert meta["frame_ms"] == 40
    frames = [decode_frame(raw) for raw in payloads]
    assert [f.sequence for f in frames] == [0, 1, 2, 3, 4]
    assert all(len(f.payload) == 16000 * 40 // 1000 * 2 for f in frames)


def test_unknown_or_bad_options_are_refused_not_ignored() -> None:
    with client_for(_speech_settings(), FakeStt()) as client:
        typo = _create(client, stream_options={"endpoint": "client"})
        bad = _create(client, stream_options={"output_frame_ms": 30})
        wrong_type = _create(client, stream_options={"tts_queue": "yes"})
    assert typo.status_code == 400 and "unknown stream option" in typo.json()["error"]["message"]
    assert bad.status_code == 400
    assert wrong_type.status_code == 400


def test_no_options_is_exactly_v1() -> None:
    assert StreamOptions.parse(None) == StreamOptions()
    assert StreamOptions().as_dict() == {
        "chunk_events": "all",
        "output_frame_ms": 20,
        "flow_control": "none",
        "endpointing": "server",
        "tts_queue": False,
    }
    with pytest.raises(InvalidRequest):
        StreamOptions.parse({"chunk_events": "some"})


# ── Input validation ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "frame,needle",
    [
        (_frame([0.0] * 960, 0, rate=48000), "sample rate"),
        (_frame([], 0, raw=b"\x00\x01\x02"), "whole number"),
        (_frame([0.0] * 16000, 0), "longer than"),
    ],
)
def test_frames_the_server_would_misread_are_refused(frame: bytes, needle: str) -> None:
    with client_for(_speech_settings(), FakeStt()) as client:
        created = _create(client).json()
        with client.websocket_connect(_url(created)) as socket:
            socket.receive_json()
            socket.send_bytes(frame)
            events, _ = _collect(socket, stop={"session.error"})
    assert events[-1]["code"] == "invalid_audio"
    assert needle in events[-1]["message"]


# ── Client endpointing: one commit, one final ────────────────────────


def test_client_endpointing_gives_exactly_one_final_per_commit() -> None:
    # With server VAD a pause mid-sentence splits one push-to-talk hold into
    # two finals. With the client owning the turn there is one, tagged with the
    # sequence of the frame that committed it.
    stt = FakeStt()
    app = create_app(_speech_settings())
    app.state.stt = stt
    with TestClient(app) as client:
        created = _create(client, mode="stt_only", stream_options={"endpointing": "client"}).json()
        with client.websocket_connect(_url(created)) as socket:
            socket.receive_json()
            seq = 0
            for block in ([0.8] * 320, [0.0] * 320, [0.0] * 320, [0.0] * 320, [0.8] * 320):
                socket.send_bytes(_frame(block, seq))
                seq += 1
            socket.send_bytes(_frame([0.0] * 320, seq, end=True))
            events, _ = _collect(socket, stop={"metrics.turn"})
    finals = [event for event in events if event["type"] == "transcript.final"]
    assert len(finals) == 1
    assert finals[0]["commit_seq"] == 5
    assert finals[0]["text"] == f"samples:{320 * 6}"
    assert stt.calls == [320 * 6]
    committed = [event for event in events if event["type"] == "audio.input.committed"]
    assert committed[0]["commit_seq"] == 5


def test_an_empty_commit_still_answers() -> None:
    stt = FakeStt()
    app = create_app(_speech_settings())
    app.state.stt = stt
    with TestClient(app) as client:
        created = _create(client, mode="stt_only", stream_options={"endpointing": "client"}).json()
        with client.websocket_connect(_url(created)) as socket:
            socket.receive_json()
            socket.send_bytes(_frame([], 7, end=True))
            events, _ = _collect(socket, stop={"transcript.final"})
    final = events[-1]
    assert final["type"] == "transcript.final"
    assert final["text"] == "" and final["no_speech"] is True and final["commit_seq"] == 7
    assert stt.calls == []


def test_a_second_commit_waits_for_the_first_instead_of_being_refused() -> None:
    stt = BlockingStt()
    app = create_app(_speech_settings())
    app.state.stt = stt
    with TestClient(app) as client:
        created = _create(client, mode="stt_only", stream_options={"endpointing": "client"}).json()
        with client.websocket_connect(_url(created)) as socket:
            socket.receive_json()
            socket.send_bytes(_frame([0.5] * 320, 0, end=True))
            assert stt.started.wait(2)
            socket.send_bytes(_frame([0.5] * 320, 1, end=True))
            stt.release.set()
            seen: list[dict] = []
            while sum(1 for e in seen if e["type"] == "transcript.final") < 2:
                message = socket.receive()
                if message.get("text"):
                    seen.append(json.loads(message["text"]))
    assert all(event.get("code") != "rate_limited" for event in seen)
    assert [e["commit_seq"] for e in seen if e["type"] == "transcript.final"] == [0, 1]


# ── Slots, queue and cancellation ────────────────────────────────────


def test_a_cancel_frees_the_slot_for_the_next_phrase_at_once() -> None:
    # v1 kept the cancelled turn in the slot until Piper noticed, so the
    # tts.speak that follows a barge-in was refused as "already running".
    engine = GatedTts()
    app = _app()
    app.state.tts = engine
    with TestClient(app) as client:
        created = _create(client, mode="tts_only").json()
        with client.websocket_connect(_url(created)) as socket:
            socket.receive_json()
            socket.send_text(json.dumps({"type": "tts.speak", "text": "One. Two.", "turn_id": "old"}))
            _collect(socket, stop={"tts.audio.chunk"})
            socket.send_text(json.dumps({"type": "turn.cancel", "turn_id": "old", "target": "tts"}))
            socket.send_text(json.dumps({"type": "tts.speak", "text": "New.", "turn_id": "new"}))
            events, _ = _collect(socket, stop={"tts.started"}, limit=40)
            engine.release.set()
    assert all(event.get("code") != "rate_limited" for event in events)
    assert events[-1] == {**events[-1], "type": "tts.started", "turn_id": "new"}
    cancelled = next(event for event in events if event["type"] == "turn.cancelled")
    assert cancelled["target"] == "tts" and cancelled["clear_audio"] is True


def test_queued_phrases_are_spoken_in_order() -> None:
    app = _app()
    app.state.tts = LongTts(0.04)
    with TestClient(app) as client:
        created = _create(client, mode="tts_only", stream_options={"tts_queue": True}).json()
        with client.websocket_connect(_url(created)) as socket:
            socket.receive_json()
            for n in range(3):
                socket.send_text(json.dumps({"type": "tts.speak", "text": f"P{n}.", "turn_id": f"p{n}"}))
            done: list[str] = []
            seen: list[dict] = []
            while len(done) < 3:
                message = socket.receive()
                if message.get("text"):
                    event = json.loads(message["text"])
                    seen.append(event)
                    if event["type"] == "tts.audio.done":
                        done.append(event["turn_id"])
    assert done == ["p0", "p1", "p2"]
    assert all(event.get("code") != "rate_limited" for event in seen)


def test_without_the_queue_option_a_busy_speak_is_still_refused() -> None:
    engine = GatedTts()
    app = _app()
    app.state.tts = engine
    with TestClient(app) as client:
        created = _create(client, mode="tts_only").json()
        with client.websocket_connect(_url(created)) as socket:
            socket.receive_json()
            socket.send_text(json.dumps({"type": "tts.speak", "text": "A. B.", "turn_id": "a"}))
            _collect(socket, stop={"tts.audio.chunk"})
            socket.send_text(json.dumps({"type": "tts.speak", "text": "C.", "turn_id": "c"}))
            events, _ = _collect(socket, stop={"session.error"})
            engine.release.set()
    assert events[-1]["code"] == "rate_limited"


def test_duplex_transcribes_while_she_is_speaking() -> None:
    # One slot used to serve both: speaking over her lost the utterance.
    engine = GatedTts()
    app = _app()
    app.state.tts = engine
    with TestClient(app) as client:
        created = _create(client, mode="duplex_speech", stream_options={"endpointing": "client"}).json()
        with client.websocket_connect(_url(created)) as socket:
            socket.receive_json()
            socket.send_text(json.dumps({"type": "tts.speak", "text": "A. B.", "turn_id": "a"}))
            _collect(socket, stop={"tts.audio.chunk"})
            socket.send_bytes(_frame([0.6] * 320, 0, end=True))
            events, _ = _collect(socket, stop={"transcript.final"}, limit=60)
            engine.release.set()
    assert events[-1]["type"] == "transcript.final"
    assert all(event.get("code") != "rate_limited" for event in events)


# ── Lifecycle ────────────────────────────────────────────────────────


def test_a_wrong_or_expired_token_is_closed_with_policy_violation() -> None:
    with client_for(_speech_settings(session_ttl_sec=1), FakeStt()) as client:
        created = _create(client).json()
        with pytest.raises(WebSocketDisconnect) as wrong:
            with client.websocket_connect(f"/v1/audio/stream/{created['session_id']}?resume_token=nope") as s:
                s.receive_text()
        store = client.app.state.speech_streams
        store._items[created["session_id"]].expires_at = time.monotonic() - 1
        with pytest.raises(WebSocketDisconnect) as expired:
            with client.websocket_connect(_url(created)) as s:
                s.receive_text()
    assert wrong.value.code == 1008 and expired.value.code == 1008


def test_a_headset_that_drops_mid_transcription_frees_the_session() -> None:
    stt = BlockingStt()
    app = create_app(_speech_settings())
    app.state.stt = stt
    with TestClient(app) as client:
        created = _create(client, mode="stt_only").json()
        with client.websocket_connect(_url(created)) as socket:
            socket.receive_json()
            socket.send_bytes(_frame([0.8] * 320, 0, end=True))
            assert stt.started.wait(2)
        # Disconnected while faster-whisper was running: the worker is told to
        # stop and the token can be used again.
        deadline = time.monotonic() + 2
        while stt.slots._value == 0 and time.monotonic() < deadline:  # type: ignore[attr-defined]
            time.sleep(0.02)
        with client.websocket_connect(_url(created)) as again:
            assert again.receive_json()["type"] == "session.ready"
    stt.release.set()


def test_the_session_store_is_bounded() -> None:
    store = SpeechStreamStore(ttl_sec=60, max_sessions=2)
    for n in range(2):
        store.put(
            SpeechStreamSession(
                f"s{n}", "tok", "stt_only", "en", "v", "faster-whisper", time.monotonic() + 60
            )
        )
    with pytest.raises(RateLimited):
        store.put(
            SpeechStreamSession("s9", "tok", "stt_only", "en", "v", "faster-whisper", time.monotonic() + 60)
        )
    with pytest.raises(Unauthenticated):
        store.acquire("s0", "other")
    assert len(store) == 2


def test_capabilities_say_whether_a_turn_would_work_now() -> None:
    with client_for(_speech_settings(), FakeStt(ready=False, reason="model-loading")) as client:
        from tests.unit.test_voice_api import auth

        body = client.get("/v1/audio/capabilities", headers=auth()).json()
    assert body["streaming"]["available"] is True
    assert body["streaming"]["stt_ready"] is False
    assert body["streaming"]["input_sample_rate"] == 16000
    assert body["streaming"]["options_supported"]["endpointing"] == ["server", "client"]


def test_the_threading_event_is_still_what_engines_watch() -> None:
    # Engines receive a threading.Event as ``cancel``; the slot must keep it so.
    from sonicagent_rt.api.websocket.speech_endpoint import _Slot

    slot = _Slot()
    _token, stop = slot.fresh()
    assert isinstance(stop, threading.Event)
    slot.cancel()
    assert stop.is_set() and slot.task is None
