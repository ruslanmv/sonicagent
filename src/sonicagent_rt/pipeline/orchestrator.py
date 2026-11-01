"""One realtime turn: endpointed audio, transcript, streamed text, phrase audio."""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import AsyncIterator

from sonicagent_rt.audio.pcm import floats_to_pcm16
from sonicagent_rt.audio.wav import decode_wav
from sonicagent_rt.config import Settings
from sonicagent_rt.pipeline.cancellation import CancellationToken
from sonicagent_rt.protocol.binary_frame import BinaryAudioFrame, encode_frame
from sonicagent_rt.protocol.constants import Codec, MessageType
from sonicagent_rt.stt.errors import Cancelled, SpeechError
from sonicagent_rt.tts.phrase_segmenter import segment_text


async def run_turn(
    *,
    samples: list[float],
    sample_rate: int,
    language: str,
    voice_id: str,
    stt: object,
    llm: object,
    tts: object,
    settings: Settings,
    cancellation: CancellationToken,
    turn_id: str,
    speech_ms: float = 0.0,
) -> AsyncIterator[dict[str, object] | bytes]:
    """Yield JSON events and encoded PCM output frames. Events contain no secrets."""
    started = time.perf_counter()
    stop = threading.Event()
    watcher = asyncio.create_task(_mirror_cancel(cancellation, stop))
    timings: dict[str, float | None] = {"stt_ms": None, "llm_first_ms": None, "tts_first_ms": None}
    sequence = 0
    try:
        yield {"type": "response.created", "turn_id": turn_id}
        transcript = await asyncio.to_thread(
            stt.transcribe,  # type: ignore[attr-defined]
            samples,
            sample_rate=sample_rate,
            language=None if language == "auto" else language,
            model=settings.stt_model,
            request_id=turn_id,
            cancel=stop,
        )
        if cancellation.cancelled:
            yield _cancelled(turn_id)
            return
        timings["stt_ms"] = _elapsed(started)
        text = transcript.text
        yield {
            "type": "transcript.final",
            "turn_id": turn_id,
            "text": text,
            "language": transcript.language,
            "is_final": True,
        }
        messages = [
            {
                "role": "system",
                "content": "Reply in one or two short spoken sentences. Do not use markdown.",
            },
            {"role": "user", "content": text},
        ]
        collected = ""
        pending = ""
        async for delta in llm.stream(messages, cancellation):  # type: ignore[attr-defined]
            if cancellation.cancelled:
                yield _cancelled(turn_id)
                return
            if timings["llm_first_ms"] is None:
                timings["llm_first_ms"] = _elapsed(started)
            collected += delta
            pending += delta
            yield {"type": "response.text.delta", "turn_id": turn_id, "delta": delta}
            ready, pending = _ready_phrases(pending, settings.tts_phrase_max_chars)
            for phrase in ready:
                async for frame in _speak(
                    phrase,
                    voice_id=voice_id,
                    language=language,
                    tts=tts,
                    settings=settings,
                    cancellation=cancellation,
                    stop=stop,
                    timings=timings,
                    started=started,
                    sequence_start=sequence,
                ):
                    if isinstance(frame, bytes):
                        sequence += 1
                    yield frame
        if pending.strip() and not cancellation.cancelled:
            async for frame in _speak(
                pending.strip(),
                voice_id=voice_id,
                language=language,
                tts=tts,
                settings=settings,
                cancellation=cancellation,
                stop=stop,
                timings=timings,
                started=started,
                sequence_start=sequence,
            ):
                if isinstance(frame, bytes):
                    sequence += 1
                yield frame
        if cancellation.cancelled:
            yield _cancelled(turn_id)
            return
        yield {"type": "response.text.done", "turn_id": turn_id}
        yield {"type": "response.audio.done", "turn_id": turn_id, "frames": sequence}
        yield {
            "type": "metrics.turn",
            "turn_id": turn_id,
            "speech_ms": round(speech_ms, 1),
            "stt_ms": timings["stt_ms"],
            "llm_first_ms": timings["llm_first_ms"],
            "tts_first_ms": timings["tts_first_ms"],
            "total_ms": _elapsed(started),
            "cancelled": False,
        }
    except Cancelled:
        yield _cancelled(turn_id)
    except SpeechError as exc:
        yield {"type": "error", "turn_id": turn_id, "code": exc.code, "message": exc.message}
    finally:
        watcher.cancel()


def _ready_phrases(buffer: str, max_chars: int) -> tuple[list[str], str]:
    normalized = " ".join(buffer.split())
    parts = segment_text(normalized, max_chars=max_chars)
    if not parts:
        return [], ""
    if normalized[-1:] not in ".!?;:":
        return parts[:-1], parts[-1]
    return parts, ""


async def _speak(
    phrase: str,
    *,
    voice_id: str,
    language: str,
    tts: object,
    settings: Settings,
    cancellation: CancellationToken,
    stop: threading.Event,
    timings: dict[str, float | None],
    started: float,
    sequence_start: int,
) -> AsyncIterator[dict[str, object] | bytes]:
    status = tts.describe()  # type: ignore[attr-defined]
    if not status.ready:
        yield {"type": "warning", "message": "speech synthesis is not ready", "code": "voice_unavailable"}
        return
    if timings["tts_first_ms"] is None:
        yield {"type": "response.audio.started", "voice_id": voice_id}
    speech = await asyncio.to_thread(
        tts.synthesize,  # type: ignore[attr-defined]
        phrase,
        voice=voice_id,
        language=None if language == "auto" else language,
        cancel=stop,
    )
    if cancellation.cancelled:
        return
    if timings["tts_first_ms"] is None:
        timings["tts_first_ms"] = _elapsed(started)
    samples, rate, _channels = decode_wav(speech.wav, max_seconds=max(settings.max_audio_seconds, 60))
    frame_samples = max(1, int(rate * settings.audio_frame_ms / 1000))
    sequence = sequence_start
    timestamp = 0
    for offset in range(0, len(samples), frame_samples):
        if cancellation.cancelled:
            return
        chunk = samples[offset : offset + frame_samples]
        payload = floats_to_pcm16(chunk)
        frame = BinaryAudioFrame(
            message_type=int(MessageType.AUDIO_OUTPUT),
            codec=int(Codec.PCM16),
            flags=0,
            sample_rate=rate,
            sequence=sequence,
            timestamp_us=timestamp,
            payload=payload,
        )
        sequence += 1
        timestamp += int(len(chunk) / rate * 1_000_000)
        yield encode_frame(frame)


def _cancelled(turn_id: str) -> dict[str, object]:
    return {"type": "response.cancelled", "turn_id": turn_id, "reason": "cancelled", "clear_audio": True}


def _elapsed(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 1)


async def _mirror_cancel(cancellation: CancellationToken, stop: threading.Event) -> None:
    await cancellation.wait()
    stop.set()
