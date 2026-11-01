"""Speech-only WebSocket. Audio in, transcript or Piper audio out. No language model.

Protocol ``sonic-speech-stream-v1``. Everything a v1 client sends and reads is
unchanged; what a session negotiated through ``stream_options`` (see
``speech_stream.store.OPTION_VALUES``) is additive and off unless asked for.

HV3 hardening, and the failure each part prevents:

* **Backpressure counted what was SENT, not what was waiting.** ``queued_ms``
  grew by one frame per frame and was never reduced, so the limit was a cap on
  the length of a reply: with the default 2000 ms, every Piper answer longer
  than two seconds died mid-sentence with "outbound audio queue is full". The
  limit now bounds audio *ahead of playback* — wall-clock pacing by default,
  the client's own ``playback.ack`` when it negotiated ``flow_control: ack`` —
  and the server waits when it is ahead instead of ending a healthy turn.
* **One slot for transcription and speech.** A user who spoke while she was
  answering had the utterance refused ("a speech turn is already running") in
  ``duplex_speech``. Recognition and synthesis now have their own slots.
* **A cancel left the cancelled turn holding the slot** until its Piper thread
  noticed, so the ``tts.speak`` that follows a barge-in was refused. A cancel
  now releases the slot at once; the old thread finishes unobserved.
* **Input was not checked against what the server decodes.** A 48 kHz frame
  was accepted and transcribed as 16 kHz (three times slow, garbage text), and
  an odd byte count crashed the PCM decoder. Both are refused with a reason.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import threading
import time
from collections import deque
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketDisconnected

from sonicagent_rt.audio.pcm import pcm16_to_floats
from sonicagent_rt.auth.service_token import enforce_origin
from sonicagent_rt.config import Settings
from sonicagent_rt.pipeline.cancellation import CancellationToken
from sonicagent_rt.protocol.binary_frame import BinaryAudioFrame, BinaryFrameError, decode_frame, encode_frame
from sonicagent_rt.protocol.constants import FLAG_END_OF_UTTERANCE, Codec, MessageType
from sonicagent_rt.protocol.sequence import SequenceError, SequenceValidator
from sonicagent_rt.speech_stream.chunks import iter_pcm16, split_frames
from sonicagent_rt.speech_stream.store import MAX_TTS_QUEUE, SpeechStreamSession
from sonicagent_rt.stt.errors import Cancelled, SpeechError
from sonicagent_rt.vad.factory import create_endpoint

router = APIRouter()
_MAX_FRAME_BYTES = 64 * 1024
#: Longest single input frame accepted. The contract is 20–40 ms; 200 ms leaves
#: room for a client that batches under load without letting one frame carry a
#: whole utterance past the per-utterance limit.
_MAX_FRAME_MS = 200
#: Transcriptions allowed to wait behind the running one (client endpointing).
_MAX_STT_PENDING = 2
#: With ``flow_control: ack``, how long the server waits for playback to move
#: before it concludes the client has stopped reading.
_ACK_STALL_SEC = 10.0
_PACE_STEP_SEC = 0.02

Emit = Callable[[dict[str, object]], Awaitable[None]]
EmitBytes = Callable[[bytes], Awaitable[None]]


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
            "options": session.options.as_dict(),
        }
    )
    stream = _Stream(websocket, session, settings, emit, emit_bytes)
    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
            if message.get("text"):
                if await stream.on_text(message["text"]):
                    await websocket.close(code=1000)
                    break
            elif message.get("bytes") is not None:
                await stream.on_audio(message["bytes"])
    except (WebSocketDisconnect, WebSocketDisconnected, RuntimeError):
        pass
    finally:
        await stream.close()
        websocket.app.state.speech_streams.release(session_id)


class _Slot:
    """One kind of work (recognition or synthesis): its task and its cancellation."""

    def __init__(self) -> None:
        self.task: asyncio.Task[None] | None = None
        self.cancellation = CancellationToken()
        self.stop = threading.Event()

    def busy(self) -> bool:
        return self.task is not None and not self.task.done()

    def fresh(self) -> tuple[CancellationToken, threading.Event]:
        self.cancellation = CancellationToken()
        self.stop = threading.Event()
        return self.cancellation, self.stop

    def cancel(self) -> None:
        """Stop the running work and free the slot NOW.

        The worker thread (Piper, faster-whisper) is told through ``stop`` and
        finishes on its own; the asyncio task is cancelled so it emits nothing
        more, and the slot is free for the next request in the same tick.
        """
        self.stop.set()
        self.cancellation.cancel()
        if self.task is not None and not self.task.done():
            self.task.cancel()
        self.task = None

    async def drain(self) -> None:
        task = self.task
        self.cancel()
        if task is not None:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task


class _Stream:
    def __init__(
        self,
        websocket: WebSocket,
        session: SpeechStreamSession,
        settings: Settings,
        emit: Emit,
        emit_bytes: EmitBytes,
    ) -> None:
        self.websocket = websocket
        self.session = session
        self.settings = settings
        self.options = session.options
        self.emit = emit
        self.emit_bytes = emit_bytes
        self.endpoint = create_endpoint(settings)
        self.sequences = SequenceValidator()
        self.started_audio = False
        self.stt = _Slot()
        self.tts = _Slot()
        self.stt_pending: deque[tuple[list[float], int | None]] = deque()
        self.tts_pending: deque[tuple[str, str]] = deque()
        # Client endpointing: the utterance being held until its commit.
        self.utterance: list[float] = []
        self.utterance_speech = False
        self.max_utterance_samples = int(
            min(settings.vad_max_utterance_sec, settings.max_audio_seconds) * settings.input_sample_rate
        )
        # Audio sent and not yet played, for the WHOLE session — not per phrase. With the queue,
        # phrases follow each other into one playback buffer on the client, so a per-phrase
        # budget let a headset hold ~2 s of unplayed audio *per queued phrase* (measured end to
        # end: 6 s of speech delivered in 2.2 s against a 2 s budget).
        #  - flow_control none: a virtual playout clock — when the last sent sample will have
        #    played if the client plays continuously from now on.
        #  - flow_control ack:  per phrase [sent_ms, played_ms], summed; a phrase leaves the
        #    table once the client reports it fully played.
        self.playout_end = 0.0
        self.unplayed: dict[str, list[float]] = {}
        self.last_ack_at: float | None = None
        self.current_tts: str | None = None

    # ── Control events ───────────────────────────────────────────────

    async def on_text(self, raw: str) -> bool:
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            await self.emit(
                {"type": "session.error", "code": "invalid_request", "message": "control event is not JSON"}
            )
            return False
        if not isinstance(event, dict):
            await self.emit(
                {
                    "type": "session.error",
                    "code": "invalid_request",
                    "message": "control event is not an object",
                }
            )
            return False
        kind = event.get("type")
        if kind == "ping":
            await self.emit({"type": "pong"})
        elif kind == "turn.cancel":
            await self._on_cancel(event)
        elif kind == "session.close":
            self.stt.cancel()
            self.tts.cancel()
            self.stt_pending.clear()
            self.tts_pending.clear()
            await self.emit({"type": "session.closed"})
            return True
        elif kind == "tts.speak":
            await self._on_speak(event)
        elif kind == "playback.ack":
            self._on_ack(event)
        else:
            await self.emit(
                {"type": "session.error", "code": "invalid_request", "message": "unsupported control event"}
            )
        return False

    async def _on_cancel(self, event: dict[str, object]) -> None:
        # v1 had one slot, so a cancel stopped whatever was running. ``target``
        # narrows it; without one both stop, which is the v1 behaviour.
        target = str(event.get("target") or "all").lower()
        if target not in ("all", "stt", "tts"):
            await self.emit(
                {
                    "type": "session.error",
                    "code": "invalid_request",
                    "message": "target must be all, stt or tts",
                }
            )
            return
        if target in ("all", "tts"):
            self.tts.cancel()
            self.tts_pending.clear()
            self._forget_playback()
        if target in ("all", "stt"):
            self.stt.cancel()
            self.stt_pending.clear()
            self.utterance = []
            self.utterance_speech = False
            with contextlib.suppress(Exception):
                self.endpoint.flush()
        await self.emit(
            {
                "type": "turn.cancelled",
                "turn_id": event.get("turn_id"),
                "target": target,
                "clear_audio": target in ("all", "tts"),
            }
        )

    async def _on_speak(self, event: dict[str, object]) -> None:
        if self.session.mode == "stt_only":
            await self.emit(
                {"type": "session.error", "code": "invalid_request", "message": "this session does not speak"}
            )
            return
        text = str(event.get("text") or "").strip()
        turn_id = str(event.get("turn_id") or f"turn_{uuid4().hex}")
        if not text:
            await self.emit(
                {
                    "type": "session.error",
                    "turn_id": turn_id,
                    "code": "invalid_request",
                    "message": "text is empty",
                }
            )
            return
        if self.tts.busy():
            if self.options.tts_queue and len(self.tts_pending) < MAX_TTS_QUEUE:
                self.tts_pending.append((text, turn_id))
                await self.emit({"type": "tts.queued", "turn_id": turn_id, "position": len(self.tts_pending)})
                return
            await self.emit(
                {
                    "type": "session.error",
                    "turn_id": turn_id,
                    "code": "rate_limited",
                    "message": "a speech turn is already running",
                }
            )
            return
        self._start_speech(text, turn_id)

    def _start_speech(self, text: str, turn_id: str) -> None:
        cancellation, stop = self.tts.fresh()
        self.tts.task = asyncio.create_task(self._speak_then_next(text, turn_id, cancellation, stop))

    async def _speak_then_next(
        self, text: str, turn_id: str, cancellation: CancellationToken, stop: threading.Event
    ) -> None:
        await self._speak(text, turn_id, cancellation, stop)
        if cancellation.cancelled or stop.is_set() or not self.tts_pending:
            return
        next_text, next_turn = self.tts_pending.popleft()
        # Started from inside the finishing task: the slot is handed straight
        # over, so no ``tts.speak`` arriving in between can jump the queue.
        cancellation, stop = self.tts.fresh()
        self.tts.task = asyncio.create_task(self._speak_then_next(next_text, next_turn, cancellation, stop))

    def _on_ack(self, event: dict[str, object]) -> None:
        if self.options.flow_control != "ack":
            return  # v1 clients never send it; a stray one is harmless
        turn_id = str(event.get("turn_id") or "")
        try:
            played = float(event.get("played_ms"))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return
        entry = self.unplayed.get(turn_id)
        if entry is None:
            return
        if played >= entry[1]:
            entry[1] = played
            self.last_ack_at = time.monotonic()
        if played > 0:
            # Playback is sequential: a phrase that has started playing means every phrase
            # sent before it has finished. Without this, a client that acknowledges only the
            # phrase it is receiving leaves the previous phrase's tail in the budget forever.
            for earlier in list(self.unplayed):
                if earlier == turn_id:
                    break
                self.unplayed.pop(earlier, None)
        # Fully played and no longer being sent: it no longer holds any of the budget.
        if entry[1] >= entry[0] and not (self.tts.busy() and self.current_tts == turn_id):
            self.unplayed.pop(turn_id, None)

    def _ahead_ms(self) -> float:
        """Audio handed to the client and not yet played, across every phrase."""
        if self.options.flow_control == "ack":
            return sum(max(0.0, sent - played) for sent, played in self.unplayed.values())
        return max(0.0, (self.playout_end - time.monotonic()) * 1000.0)

    def _note_sent(self, turn_id: str, ms: float) -> None:
        if self.options.flow_control == "ack":
            self.unplayed.setdefault(turn_id, [0.0, 0.0])[0] += ms
        else:
            self.playout_end = max(self.playout_end, time.monotonic()) + ms / 1000.0

    def _forget_playback(self) -> None:
        """The client cleared its audio (a tts cancel): nothing it held is waiting any more."""
        self.unplayed.clear()
        self.playout_end = 0.0

    # ── Microphone audio ─────────────────────────────────────────────

    async def on_audio(self, payload: bytes) -> None:
        if self.session.mode == "tts_only":
            await self.emit(
                {
                    "type": "session.error",
                    "code": "invalid_request",
                    "message": "this session does not accept audio",
                }
            )
            return
        if len(payload) > _MAX_FRAME_BYTES:
            await self.emit(
                {"type": "session.error", "code": "audio_too_large", "message": "audio frame is too large"}
            )
            return
        try:
            frame = decode_frame(payload)
            if frame.message_type != int(MessageType.AUDIO_INPUT):
                raise BinaryFrameError("client frames must be microphone audio")
            if frame.sample_rate != self.settings.input_sample_rate:
                raise BinaryFrameError(
                    f"unsupported sample rate {frame.sample_rate}: send mono PCM16 at "
                    f"{self.settings.input_sample_rate} Hz"
                )
            if len(frame.payload) % 2:
                raise BinaryFrameError("PCM16 payload must be a whole number of 16-bit samples")
            if len(frame.payload) // 2 > self.settings.input_sample_rate * _MAX_FRAME_MS // 1000:
                raise BinaryFrameError(f"audio frame is longer than {_MAX_FRAME_MS} ms")
            self.sequences.accept(frame.sequence)
            samples = pcm16_to_floats(frame.payload)
        except (BinaryFrameError, SequenceError, ValueError) as exc:
            await self.emit({"type": "session.error", "code": "invalid_audio", "message": str(exc)})
            return
        if not self.started_audio:
            self.started_audio = True
            await self.emit({"type": "audio.input.started"})
        committed = bool(frame.flags & FLAG_END_OF_UTTERANCE)
        if self.options.endpointing == "client":
            await self._client_endpointed(samples, committed, frame.sequence)
            return
        for event in self.endpoint.push(samples):
            if event.kind == "started":
                await self.emit({"type": "speech.started"})
            elif event.kind == "utterance":
                await self._transcribe(event.samples, None)
        if committed:
            await self.emit({"type": "audio.input.committed", "commit_seq": frame.sequence})
            for event in self.endpoint.flush():
                if event.kind == "utterance":
                    await self._transcribe(event.samples, frame.sequence)

    async def _client_endpointed(self, samples: list[float], committed: bool, sequence: int) -> None:
        # The VAD still runs, but only to say "speech.started" for the UI; the
        # client's commit decides where the utterance ends.
        for event in self.endpoint.push(samples):
            if event.kind == "started" and not self.utterance_speech:
                self.utterance_speech = True
                await self.emit({"type": "speech.started"})
        self.utterance.extend(samples)
        if len(self.utterance) > self.max_utterance_samples:
            self.utterance = []
            self.utterance_speech = False
            with contextlib.suppress(Exception):
                self.endpoint.flush()
            await self.emit(
                {
                    "type": "session.error",
                    "code": "audio_too_long",
                    "commit_seq": None,
                    "message": "utterance is longer than the server accepts; it was discarded",
                }
            )
            return
        if not committed:
            return
        held, self.utterance = self.utterance, []
        self.utterance_speech = False
        with contextlib.suppress(Exception):
            self.endpoint.flush()
        await self.emit({"type": "audio.input.committed", "commit_seq": sequence})
        await self._transcribe(held, sequence)

    async def _transcribe(self, samples: list[float], commit_seq: int | None) -> None:
        if self.stt.busy():
            if self.options.endpointing == "client" and len(self.stt_pending) < _MAX_STT_PENDING:
                self.stt_pending.append((samples, commit_seq))
                return
            await self.emit(
                {
                    "type": "session.error",
                    "code": "rate_limited",
                    "commit_seq": commit_seq,
                    "message": "a speech turn is already running",
                }
            )
            return
        self._start_transcription(samples, commit_seq)

    def _start_transcription(self, samples: list[float], commit_seq: int | None) -> None:
        cancellation, stop = self.stt.fresh()
        self.stt.task = asyncio.create_task(
            self._transcribe_then_next(samples, commit_seq, cancellation, stop)
        )

    async def _transcribe_then_next(
        self,
        samples: list[float],
        commit_seq: int | None,
        cancellation: CancellationToken,
        stop: threading.Event,
    ) -> None:
        await self._finish_utterance(samples, commit_seq, cancellation, stop)
        if cancellation.cancelled or stop.is_set() or not self.stt_pending:
            return
        next_samples, next_seq = self.stt_pending.popleft()
        cancellation, stop = self.stt.fresh()
        self.stt.task = asyncio.create_task(
            self._transcribe_then_next(next_samples, next_seq, cancellation, stop)
        )

    async def _finish_utterance(
        self,
        samples: list[float],
        commit_seq: int | None,
        cancellation: CancellationToken,
        stop: threading.Event,
    ) -> None:
        turn_id = f"turn_{uuid4().hex}"
        audio_ms = round(len(samples) * 1000 / self.settings.input_sample_rate)
        tag: dict[str, object] = {} if commit_seq is None else {"commit_seq": commit_seq}
        try:
            await self.emit({"type": "speech.stopped", "turn_id": turn_id, **tag})
            if cancellation.cancelled or stop.is_set():
                return
            if not samples:
                # A commit with no audio still answers, so the client is never
                # left waiting for a final that is not coming.
                await self.emit(
                    {
                        "type": "transcript.final",
                        "turn_id": turn_id,
                        "text": "",
                        "language": self.session.language,
                        "is_final": True,
                        "no_speech": True,
                        "audio_ms": 0,
                        **tag,
                    }
                )
                return
            started = time.perf_counter()
            transcript = await asyncio.to_thread(
                self.websocket.app.state.stt.transcribe,
                samples,
                sample_rate=self.settings.input_sample_rate,
                language=self.session.language,
                model=self.settings.stt_model,
                request_id=turn_id,
                cancel=stop,
            )
            if cancellation.cancelled or stop.is_set():
                return
            elapsed = round((time.perf_counter() - started) * 1000, 1)
            await self.emit(
                {
                    "type": "transcript.final",
                    "turn_id": turn_id,
                    "text": transcript.text,
                    "language": transcript.language,
                    "is_final": True,
                    "audio_ms": audio_ms,
                    **tag,
                }
            )
            await self.emit(
                {
                    "type": "metrics.turn",
                    "turn_id": turn_id,
                    "stt_ms": elapsed,
                    "audio_ms": audio_ms,
                    "partials": 0,
                    "llm": False,
                    **tag,
                }
            )
        except Cancelled:
            return
        except asyncio.CancelledError:
            raise
        except SpeechError as exc:
            await self.emit(
                {"type": "session.error", "turn_id": turn_id, "code": exc.code, "message": exc.message, **tag}
            )
        except (WebSocketDisconnect, WebSocketDisconnected):
            return

    # ── Synthesis ────────────────────────────────────────────────────

    async def _speak(
        self, text: str, turn_id: str, cancellation: CancellationToken, stop: threading.Event
    ) -> None:
        settings = self.settings
        frame_ms = int(self.options.output_frame_ms)
        limit_ms = settings.max_outbound_queue_ms
        started = time.perf_counter()
        first_ms: float | None = None
        sequence = 0
        sent_ms = 0.0
        self.current_tts = turn_id
        await self.emit({"type": "tts.started", "turn_id": turn_id, "voice_id": self.session.voice_id})
        iterator = iter(
            iter_pcm16(
                self.websocket.app.state.tts,
                text,
                voice=self.session.voice_id,
                language=self.session.language,
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
                    await self.emit(
                        {
                            "type": "tts.audio.meta",
                            "turn_id": turn_id,
                            "sample_rate": rate,
                            "codec": "pcm_s16le",
                            "incremental": "sentence",
                            "frame_ms": frame_ms,
                        }
                    )
                for piece in split_frames(pcm, rate, frame_ms):
                    if cancellation.cancelled or stop.is_set():
                        return
                    if limit_ms <= 0:
                        # A zero budget cannot hold even one frame: refuse, as v1 did.
                        await self._refuse_queue(turn_id, cancellation, stop, "outbound audio queue is full")
                        return
                    if not await self._wait_for_room(turn_id, limit_ms, cancellation, stop):
                        return
                    timestamp = sequence * frame_ms * 1000
                    if self.options.chunk_events == "all":
                        await self.emit(
                            {
                                "type": "tts.audio.chunk",
                                "turn_id": turn_id,
                                "sequence": sequence,
                                "sample_rate": rate,
                                "timestamp_us": timestamp,
                                "bytes": len(piece),
                            }
                        )
                    await self.emit_bytes(
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
                    piece_ms = len(piece) / 2 / rate * 1000.0
                    sent_ms += piece_ms
                    self._note_sent(turn_id, piece_ms)
                    sequence += 1
        except Cancelled:
            return
        except SpeechError as exc:
            await self.emit(
                {"type": "session.error", "turn_id": turn_id, "code": exc.code, "message": exc.message}
            )
            return
        except (WebSocketDisconnect, WebSocketDisconnected):
            return
        await self.emit(
            {"type": "tts.audio.done", "turn_id": turn_id, "frames": sequence, "audio_ms": round(sent_ms)}
        )
        await self.emit(
            {
                "type": "metrics.turn",
                "turn_id": turn_id,
                "tts_first_ms": first_ms,
                "frames": sequence,
                "audio_ms": round(sent_ms),
                "llm": False,
            }
        )

    async def _wait_for_room(
        self,
        turn_id: str,
        limit_ms: int,
        cancellation: CancellationToken,
        stop: threading.Event,
    ) -> bool:
        """Hold the next frame while the client has ``limit_ms`` or more unplayed.

        Pacing, not refusing: the reply is healthy, the client is simply not
        there yet. Only a client that negotiated acks and then stopped
        acknowledging for ``_ACK_STALL_SEC`` is treated as gone.
        """
        waiting_since = time.monotonic()
        while self._ahead_ms() >= limit_ms:
            if cancellation.cancelled or stop.is_set():
                return False
            if self.options.flow_control == "ack":
                last = self.last_ack_at or waiting_since
                if time.monotonic() - max(last, waiting_since) > _ACK_STALL_SEC:
                    await self._refuse_queue(
                        turn_id, cancellation, stop, "client stopped acknowledging playback"
                    )
                    return False
            await asyncio.sleep(_PACE_STEP_SEC)
        return True

    async def _refuse_queue(
        self, turn_id: str, cancellation: CancellationToken, stop: threading.Event, message: str
    ) -> None:
        cancellation.cancel()
        stop.set()
        await self.emit(
            {"type": "session.error", "turn_id": turn_id, "code": "rate_limited", "message": message}
        )

    async def close(self) -> None:
        self.stt_pending.clear()
        self.tts_pending.clear()
        await self.stt.drain()
        await self.tts.drain()
