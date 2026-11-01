"""Speech-only WebSocket. Audio in, transcript or Piper audio out. No language model."""

from __future__ import annotations

import asyncio
import contextlib
import json
import threading
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketDisconnected

from sonicagent_rt.audio.pcm import pcm16_to_floats
from sonicagent_rt.config import Settings
from sonicagent_rt.auth.service_token import enforce_origin
from sonicagent_rt.pipeline.cancellation import CancellationToken
from sonicagent_rt.protocol.binary_frame import BinaryAudioFrame, BinaryFrameError, decode_frame, encode_frame
from sonicagent_rt.protocol.constants import FLAG_END_OF_UTTERANCE, Codec, MessageType
from sonicagent_rt.protocol.sequence import SequenceError, SequenceValidator
from sonicagent_rt.speech_stream.chunks import iter_pcm16, split_frames
from sonicagent_rt.speech_stream.store import SpeechStreamSession
from sonicagent_rt.stt.errors import Cancelled, SpeechError
from sonicagent_rt.vad.factory import create_endpoint

router = APIRouter()
_MAX_FRAME_BYTES = 64 * 1024
Emit = Callable[[dict[str, object]], Awaitable[None]]


@router.websocket("/audio/stream/{session_id}")
async def speech_stream(websocket: WebSocket, session_id: str) -> None:
    settings: Settings = websocket.app.state.settings
    token = websocket.query_params.get("resume_token", "")
    try:
        if not settings.voice_enabled:
            raise SpeechError("voice endpoints are disabled")
        enforce_origin(websocket.headers.get("origin"), settings)
        session = websocket.app.state.speech_streams.acquire(session_id, token)
    except SpeechError:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    opened = time.monotonic()
    send_lock = asyncio.Lock()

    async def emit(payload: dict[str, object]) -> None:
        payload.setdefault("t_ms", int((time.monotonic() - opened) * 1000))
        async with send_lock:
            await websocket.send_json(payload)

    async def emit_bytes(payload: bytes) -> None:
        async with send_lock:
            await websocket.send_bytes(payload)

    await emit(
        {
            "type": "session.ready",
            "protocol": "sonic-speech-stream-v1",
            "session_id": session.session_id,
            "mode": session.mode,
            "llm": False,
            "partial_results": False,
        }
    )
    endpoint = create_endpoint(settings)
    sequences = SequenceValidator()
    cancellation = CancellationToken()
    stop = threading.Event()
    turn_task: asyncio.Task[None] | None = None
    started_audio = False

    def busy() -> bool:
        return turn_task is not None and not turn_task.done()

    def replace_turn() -> tuple[CancellationToken, threading.Event]:
        nonlocal cancellation, stop
        cancellation = CancellationToken()
        stop = threading.Event()
        return cancellation, stop

    async def start_transcription(samples: list[float]) -> None:
        nonlocal turn_task
        if busy():
            await emit(
                {"type": "session.error", "code": "rate_limited", "message": "a speech turn is already running"}
            )
            return
        token_box, stop_box = replace_turn()
        turn_task = asyncio.create_task(
            _finish_utterance(websocket, samples, session, settings, token_box, stop_box, emit)
        )

    async def start_speech(text: str, turn_id: str) -> None:
        nonlocal turn_task
        if busy():
            await emit(
                {"type": "session.error", "code": "rate_limited", "message": "a speech turn is already running"}
            )
            return
        token_box, stop_box = replace_turn()
        turn_task = asyncio.create_task(
            _speak(websocket, text, turn_id, session, settings, token_box, stop_box, emit, emit_bytes)
        )

    try:
        while True:
            message = await websocket.receive()
            if message.get("text"):
                closed = await _on_text(message["text"], session, cancellation, stop, emit, start_speech)
                if closed:
                    await websocket.close(code=1000)
                    break
            elif message.get("bytes") is not None:
                if session.mode == "tts_only":
                    await emit(
                        {
                            "type": "session.error",
                            "code": "invalid_request",
                            "message": "this session does not accept audio",
                        }
                    )
                    continue
                accepted = await _on_audio(
                    message["bytes"],
                    settings,
                    endpoint,
                    sequences,
                    emit,
                    start_transcription,
                    started_audio,
                )
                if accepted:
                    started_audio = True
    except (WebSocketDisconnect, WebSocketDisconnected):
        stop.set()
        cancellation.cancel()
    finally:
        stop.set()
        cancellation.cancel()
        if turn_task is not None and not turn_task.done():
            turn_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await turn_task
        websocket.app.state.speech_streams.release(session_id)


async def _on_text(
    raw: str,
    session: SpeechStreamSession,
    cancellation: CancellationToken,
    stop: threading.Event,
    emit: Emit,
    start_speech,
) -> bool:
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        await emit({"type": "session.error", "code": "invalid_request", "message": "control event is not JSON"})
        return False
    kind = event.get("type")
    if kind == "ping":
        await emit({"type": "pong"})
    elif kind == "turn.cancel":
        stop.set()
        cancellation.cancel()
        await emit({"type": "turn.cancelled", "turn_id": event.get("turn_id"), "clear_audio": True})
    elif kind == "session.close":
        stop.set()
        cancellation.cancel()
        await emit({"type": "session.closed"})
        return True
    elif kind == "tts.speak":
        if session.mode == "stt_only":
            await emit({"type": "session.error", "code": "invalid_request", "message": "this session does not speak"})
            return False
        text = str(event.get("text") or "").strip()
        turn_id = str(event.get("turn_id") or f"turn_{uuid4().hex}")
        if not text:
            await emit(
                {"type": "session.error", "turn_id": turn_id, "code": "invalid_request", "message": "text is empty"}
            )
            return False
        await start_speech(text, turn_id)
    else:
        await emit({"type": "session.error", "code": "invalid_request", "message": "unsupported control event"})
    return False


async def _on_audio(
    payload: bytes,
    settings: Settings,
    endpoint: object,
    sequences: SequenceValidator,
    emit: Emit,
    start_transcription,
    started_audio: bool,
) -> bool:
    if len(payload) > _MAX_FRAME_BYTES:
        await emit({"type": "session.error", "code": "audio_too_large", "message": "audio frame is too large"})
        return False
    try:
        frame = decode_frame(payload)
        if frame.message_type != int(MessageType.AUDIO_INPUT):
            raise BinaryFrameError("client frames must be microphone audio")
        sequences.accept(frame.sequence)
        samples = pcm16_to_floats(frame.payload)
    except (BinaryFrameError, SequenceError, ValueError) as exc:
        await emit({"type": "session.error", "code": "invalid_audio", "message": str(exc)})
        return False
    if not started_audio:
        await emit({"type": "audio.input.started"})
    for event in endpoint.push(samples):  # type: ignore[attr-defined]
        if event.kind == "started":
            await emit({"type": "speech.started"})
        elif event.kind == "utterance":
            await start_transcription(event.samples)
    if frame.flags & FLAG_END_OF_UTTERANCE:
        await emit({"type": "audio.input.committed"})
        for event in endpoint.flush():  # type: ignore[attr-defined]
            if event.kind == "utterance":
                await start_transcription(event.samples)
    return True


async def _finish_utterance(
    websocket: WebSocket,
    samples: list[float],
    session: SpeechStreamSession,
    settings: Settings,
    cancellation: CancellationToken,
    stop: threading.Event,
    emit: Emit,
) -> None:
    turn_id = f"turn_{uuid4().hex}"
    try:
        await emit({"type": "speech.stopped", "turn_id": turn_id})
        if cancellation.cancelled or stop.is_set():
            return
        started = time.perf_counter()
        transcript = await asyncio.to_thread(
            websocket.app.state.stt.transcribe,
            samples,
            sample_rate=settings.input_sample_rate,
            language=session.language,
            model=settings.stt_model,
            request_id=turn_id,
            cancel=stop,
        )
        if cancellation.cancelled or stop.is_set():
            return
        elapsed = round((time.perf_counter() - started) * 1000, 1)
        await emit(
            {
                "type": "transcript.final",
                "turn_id": turn_id,
                "text": transcript.text,
                "language": transcript.language,
                "is_final": True,
            }
        )
        await emit({"type": "metrics.turn", "turn_id": turn_id, "stt_ms": elapsed, "partials": 0, "llm": False})
    except Cancelled:
        return
    except asyncio.CancelledError:
        raise
    except SpeechError as exc:
        await emit({"type": "session.error", "turn_id": turn_id, "code": exc.code, "message": exc.message})
    except (WebSocketDisconnect, WebSocketDisconnected):
        return


async def _speak(
    websocket: WebSocket,
    text: str,
    turn_id: str,
    session: SpeechStreamSession,
    settings: Settings,
    cancellation: CancellationToken,
    stop: threading.Event,
    emit: Emit,
    emit_bytes,
) -> None:
    started = time.perf_counter()
    first_ms: float | None = None
    sequence = 0
    queued_ms = 0
    await emit({"type": "tts.started", "turn_id": turn_id, "voice_id": session.voice_id})
    iterator = iter(
        iter_pcm16(
            websocket.app.state.tts,
            text,
            voice=session.voice_id,
            language=session.language,
            cancel=stop,
        )
    )

    def pull() -> tuple[int, bytes] | None:
        try:
            return next(iterator)
        except StopIteration:
            return None

    try:
        while True:
            if cancellation.cancelled or stop.is_set():
                return
            chunk = await asyncio.to_thread(pull)
            if chunk is None:
                break
            rate, pcm = chunk
            if first_ms is None:
                first_ms = round((time.perf_counter() - started) * 1000, 1)
                await emit(
                    {
                        "type": "tts.audio.meta",
                        "turn_id": turn_id,
                        "sample_rate": rate,
                        "codec": "pcm_s16le",
                        "incremental": "sentence",
                    }
                )
            for piece in split_frames(pcm, rate, settings.audio_frame_ms):
                if cancellation.cancelled or stop.is_set():
                    return
                queued_ms += settings.audio_frame_ms
                if queued_ms > settings.max_outbound_queue_ms:
                    cancellation.cancel()
                    stop.set()
                    await emit(
                        {
                            "type": "session.error",
                            "turn_id": turn_id,
                            "code": "rate_limited",
                            "message": "outbound audio queue is full",
                        }
                    )
                    return
                timestamp = sequence * settings.audio_frame_ms * 1000
                await emit(
                    {
                        "type": "tts.audio.chunk",
                        "turn_id": turn_id,
                        "sequence": sequence,
                        "sample_rate": rate,
                        "timestamp_us": timestamp,
                        "bytes": len(piece),
                    }
                )
                await emit_bytes(
                    encode_frame(
                        BinaryAudioFrame(
                            message_type=int(MessageType.AUDIO_OUTPUT),
                            codec=int(Codec.PCM16),
                            flags=0,
                            sample_rate=rate,
                            sequence=sequence,
                            timestamp_us=timestamp,
                            payload=piece,
                        )
                    )
                )
                sequence += 1
    except Cancelled:
        return
    except SpeechError as exc:
        await emit({"type": "session.error", "turn_id": turn_id, "code": exc.code, "message": exc.message})
        return
    except (WebSocketDisconnect, WebSocketDisconnected):
        return
    await emit({"type": "tts.audio.done", "turn_id": turn_id, "frames": sequence})
    await emit(
        {"type": "metrics.turn", "turn_id": turn_id, "tts_first_ms": first_ms, "frames": sequence, "llm": False}
    )
