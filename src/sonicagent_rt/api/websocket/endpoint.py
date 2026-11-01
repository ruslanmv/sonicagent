"""Authenticated realtime turns over binary PCM frames."""

from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketDisconnected

from sonicagent_rt.audio.pcm import pcm16_to_floats
from sonicagent_rt.auth.service_token import enforce_origin
from sonicagent_rt.observability.stt_metrics import REALTIME_INFLIGHT, observe_realtime_turn
from sonicagent_rt.pipeline.cancellation import CancellationToken
from sonicagent_rt.pipeline.orchestrator import run_turn
from sonicagent_rt.protocol.binary_frame import BinaryFrameError, decode_frame
from sonicagent_rt.protocol.constants import FLAG_END_OF_UTTERANCE, MessageType
from sonicagent_rt.protocol.sequence import SequenceError, SequenceValidator
from sonicagent_rt.stt.errors import SpeechError
from sonicagent_rt.vad.factory import create_endpoint, vad_backend

router = APIRouter()

_MAX_FRAME_BYTES = 64 * 1024


@router.websocket("/realtime/{session_id}")
async def realtime(websocket: WebSocket, session_id: str) -> None:
    settings = websocket.app.state.settings
    token = websocket.query_params.get("resume_token", "")
    try:
        if not settings.voice_enabled:
            raise SpeechError("voice endpoints are disabled")
        enforce_origin(websocket.headers.get("origin"), settings)
        session, resumed = websocket.app.state.sessions.acquire(session_id, token)
    except SpeechError:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    hello = "session.updated" if resumed else "session.created"
    await websocket.send_json(
        {
            "type": hello,
            "session_id": session.session_id,
            "status": "ready",
            "vad": vad_backend(settings),
            "resumed": resumed,
        }
    )
    endpoint = create_endpoint(settings)
    sequences = SequenceValidator()
    turn: object | None = None
    cancellation: CancellationToken | None = None

    async def cancel_turn(reason: str) -> None:
        nonlocal cancellation
        if cancellation is not None and not cancellation.cancelled:
            cancellation.cancel()
            return
        await websocket.send_json({"type": "response.cancelled", "reason": reason})

    async def start_turn(samples: list[float]) -> None:
        nonlocal turn, cancellation
        if cancellation is not None:
            cancellation.cancel()
        cancellation = CancellationToken()
        token_box = cancellation
        turn_id = f"turn_{uuid4().hex}"

        async def pump() -> None:
            queued_ms = 0
            recorded = False
            REALTIME_INFLIGHT.inc()
            try:
                async for item in run_turn(
                    samples=samples,
                    sample_rate=settings.input_sample_rate,
                    language=session.language,
                    voice_id=session.voice_id,
                    stt=websocket.app.state.stt,
                    llm=websocket.app.state.llm,
                    tts=websocket.app.state.tts,
                    settings=settings,
                    cancellation=token_box,
                    turn_id=turn_id,
                    speech_ms=len(samples) * 1000 / settings.input_sample_rate,
                ):
                    if token_box.cancelled and not isinstance(item, dict):
                        break
                    terminal = {"metrics.turn", "response.cancelled", "error"}
                    if isinstance(item, dict) and not recorded and item.get("type") in terminal:
                        recorded = True
                        kind = item.get("type")
                        result = {"metrics.turn": "ok", "response.cancelled": "cancelled"}.get(str(kind), "error")
                        observe_realtime_turn(result, item)
                    if isinstance(item, bytes):
                        queued_ms += settings.audio_frame_ms
                        if queued_ms > settings.max_outbound_queue_ms:
                            token_box.cancel()
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "turn_id": turn_id,
                                    "code": "rate_limited",
                                    "message": "outbound audio queue is full",
                                }
                            )
                            break
                        await websocket.send_bytes(item)
                    else:
                        await websocket.send_json(item)
            except Exception:
                if not recorded:
                    observe_realtime_turn("error", {})
                await websocket.send_json(
                    {"type": "error", "turn_id": turn_id, "code": "inference_failed", "message": "turn failed"}
                )
            finally:
                REALTIME_INFLIGHT.dec()

        import asyncio

        turn = asyncio.create_task(pump())

    try:
        while True:
            message = await websocket.receive()
            if message.get("text"):
                await _on_text(websocket, message["text"], cancel_turn)
            elif message.get("bytes") is not None:
                payload = message["bytes"]
                if len(payload) > _MAX_FRAME_BYTES:
                    await websocket.send_json(
                        {"type": "error", "code": "audio_too_large", "message": "audio frame is too large"}
                    )
                    continue
                try:
                    frame = decode_frame(payload)
                    if frame.message_type != int(MessageType.AUDIO_INPUT):
                        raise BinaryFrameError("client frames must be microphone audio")
                    sequences.accept(frame.sequence)
                    samples = pcm16_to_floats(frame.payload)
                except (BinaryFrameError, SequenceError, ValueError) as exc:
                    await websocket.send_json({"type": "error", "code": "invalid_audio", "message": str(exc)})
                    continue
                if (
                    settings.barge_in_enabled
                    and turn is not None
                    and not turn.done()
                    and _rms(samples) >= settings.vad_threshold
                ):
                    await cancel_turn("barge-in")
                for event in endpoint.push(samples):
                    if event.kind == "started":
                        await websocket.send_json({"type": "speech.started"})
                    elif event.kind == "utterance":
                        await websocket.send_json({"type": "speech.stopped"})
                        await start_turn(event.samples)
                if frame.flags & FLAG_END_OF_UTTERANCE:
                    for event in endpoint.flush():
                        if event.kind == "utterance":
                            await websocket.send_json({"type": "speech.stopped"})
                            await start_turn(event.samples)
    except (WebSocketDisconnect, WebSocketDisconnected):
        if cancellation is not None:
            cancellation.cancel()
    finally:
        websocket.app.state.sessions.release(session_id)


async def _on_text(websocket: WebSocket, raw: str, cancel_turn) -> None:
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        await websocket.send_json({"type": "error", "code": "invalid_request", "message": "control event is not JSON"})
        return
    kind = event.get("type")
    if kind == "ping":
        await websocket.send_json({"type": "pong"})
    elif kind == "response.cancel":
        await cancel_turn("client")
    elif kind == "call.end":
        await websocket.close(code=1000)
    else:
        await websocket.send_json({"type": "error", "code": "invalid_request", "message": "unsupported control event"})


def _rms(samples: list[float]) -> float:
    if not samples:
        return 0.0
    total = sum(sample * sample for sample in samples)
    return (total / len(samples)) ** 0.5
