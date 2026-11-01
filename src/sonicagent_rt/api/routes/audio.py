"""Batch speech HTTP API used by OllaBridge and local clients."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import threading
import time
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from sonicagent_rt.api.errors import error_response
from sonicagent_rt.api.realtime_status import realtime_status
from sonicagent_rt.audio.decode import decode_audio, is_silence
from sonicagent_rt.auth.service_token import enforce_origin, require_api_key
from sonicagent_rt.config import Settings
from sonicagent_rt.observability.stt_metrics import observe_stt, observe_tts
from sonicagent_rt.stt.errors import (
    AudioTooLarge,
    DuplicateRequest,
    InferenceFailed,
    InferenceTimeout,
    InvalidAudio,
    InvalidRequest,
    ModelUnavailable,
    SpeechError,
    UnsupportedFormat,
    VoiceDisabled,
)
from sonicagent_rt.stt.language_detection import normalize_language
from sonicagent_rt.stt.models import public_model_id

logger = logging.getLogger("sonicagent_rt.api.audio")
router = APIRouter(prefix="/audio", tags=["audio"])
_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class InFlightRequests:
    def __init__(self) -> None:
        self._ids: set[str] = set()
        self._lock = threading.Lock()

    def start(self, request_id: str) -> None:
        with self._lock:
            if request_id in self._ids:
                raise DuplicateRequest("a request with this id is already running")
            self._ids.add(request_id)

    def finish(self, request_id: str) -> None:
        with self._lock:
            self._ids.discard(request_id)


class SpeechRequest(BaseModel):
    text: str
    voice: str | None = None
    language: str | None = None
    format: str = "wav"
    request_id: str | None = None


class TranscriptionResponse(BaseModel):
    text: str
    language: str
    model: str
    is_final: bool
    request_id: str
    duration_ms: int = Field(description="Measured decoded audio duration in milliseconds.")


async def require_audio_access(request: Request) -> None:
    settings: Settings = request.app.state.settings
    if not settings.voice_enabled:
        raise VoiceDisabled("voice endpoints are disabled")
    token = require_api_key(request.headers.get("authorization"), settings)
    enforce_origin(request.headers.get("origin"), settings)
    key = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    request.app.state.rate_limiter.check(key)


@router.get("/capabilities")
async def capabilities(request: Request, _: None = Depends(require_audio_access)) -> dict[str, object]:
    settings: Settings = request.app.state.settings
    stt = request.app.state.stt.describe()
    tts = request.app.state.tts.describe()
    return {
        "version": 1,
        "stt": {
            "available": bool(stt.available),
            "ready": bool(stt.ready),
            "mode": "batch",
            "languages": settings.parsed_stt_languages(),
            "models": [stt.model] if stt.model else [],
            "max_seconds": settings.max_audio_seconds,
            "max_upload_bytes": settings.max_upload_bytes,
            "reason": stt.reason,
        },
        "tts": tts.as_dict(),
        "realtime": realtime_status(settings, stt),
        "route": {"location": "sonicagent"},
    }


@router.post("/transcriptions", response_model=TranscriptionResponse)
async def transcribe(
    request: Request,
    file: UploadFile | None = File(default=None),
    audio: UploadFile | None = File(default=None),
    language: str | None = Form(default=None),
    model: str | None = Form(default=None),
    request_id: str | None = Form(default=None),
    _: None = Depends(require_audio_access),
) -> Response:
    settings: Settings = request.app.state.settings
    started = time.perf_counter()
    validated_id: str | None = None
    try:
        validated_id = resolve_request_id(request_id, request.headers.get("x-request-id"))
        request.app.state.inflight.start(validated_id)
        try:
            payload = await _transcription_body(
                request,
                settings,
                file=file or audio,
                language=language,
                model=model,
                request_id=validated_id,
            )
        finally:
            request.app.state.inflight.finish(validated_id)
        observe_stt("ok", "ok", time.perf_counter() - started, payload.duration_ms / 1000)
        logger.info(
            "stt result=ok code=ok request_id=%s duration_ms=%s processing_ms=%s",
            validated_id,
            payload.duration_ms,
            int((time.perf_counter() - started) * 1000),
        )
        return JSONResponse(content=payload.model_dump(), headers={"Cache-Control": "no-store"})
    except SpeechError as exc:
        observe_stt("error", exc.code, time.perf_counter() - started, 0)
        logger.info("stt result=error code=%s request_id=%s", exc.code, validated_id or "")
        return error_response(exc, validated_id)
    except Exception:
        logger.exception("stt result=error code=inference_failed request_id=%s", validated_id or "")
        observe_stt("error", "inference_failed", time.perf_counter() - started, 0)
        return error_response(InferenceFailed("transcription failed"), validated_id)


@router.post("/speech")
async def synthesize(request: Request, body: SpeechRequest, _: None = Depends(require_audio_access)) -> Response:
    settings: Settings = request.app.state.settings
    validated_id: str | None = None
    try:
        if body.format.strip().lower() != "wav":
            raise UnsupportedFormat("only wav output is supported")
        validated_id = resolve_request_id(body.request_id, request.headers.get("x-request-id"))
        language = normalize_language(body.language, allowed=settings.parsed_stt_languages(), default="en")
        cancel = threading.Event()
        watcher = asyncio.create_task(_watch_disconnect(request, cancel))
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    request.app.state.tts.synthesize,
                    body.text,
                    voice=body.voice or settings.tts_voice,
                    language=language,
                    cancel=cancel,
                ),
                timeout=settings.tts_timeout_sec,
            )
        except TimeoutError as exc:
            cancel.set()
            raise InferenceTimeout("synthesis exceeded the processing deadline") from exc
        finally:
            cancel.set()
            watcher.cancel()
        observe_tts("ok", "ok")
        logger.info("tts result=ok code=ok request_id=%s voice=%s", validated_id, result.voice)
        return Response(
            content=result.wav,
            media_type="audio/wav",
            headers={
                "Cache-Control": "no-store",
                "X-Request-Id": validated_id,
                "X-Sonic-Voice": result.voice,
                "X-Sonic-Sample-Rate": str(result.sample_rate),
            },
        )
    except SpeechError as exc:
        observe_tts("error", exc.code)
        logger.info("tts result=error code=%s request_id=%s", exc.code, validated_id or "")
        return error_response(exc, validated_id)
    except Exception:
        logger.exception("tts result=error code=inference_failed request_id=%s", validated_id or "")
        observe_tts("error", "inference_failed")
        return error_response(InferenceFailed("speech synthesis failed"), validated_id)


async def _transcription_body(
    request: Request,
    settings: Settings,
    *,
    file: UploadFile | None,
    language: str | None,
    model: str | None,
    request_id: str,
) -> TranscriptionResponse:
    if file is None:
        raise InvalidAudio("an audio file is required")
    selected_language = normalize_language(
        language,
        allowed=settings.parsed_stt_languages(),
        default=settings.stt_language,
    )
    model_name = public_model_id(model or settings.stt_model)
    payload = await _read_bounded(file, settings.max_upload_bytes)
    decoded = decode_audio(
        payload,
        content_type=file.content_type,
        filename=file.filename,
        max_seconds=settings.max_audio_seconds,
    )
    if is_silence(decoded.samples, settings.stt_silence_rms):
        status = request.app.state.stt.describe()
        if not status.available:
            raise ModelUnavailable("speech engine is not available")
        return TranscriptionResponse(
            text="",
            language=selected_language or "und",
            model=model_name,
            is_final=True,
            request_id=request_id,
            duration_ms=decoded.duration_ms,
        )
    cancel = threading.Event()
    watcher = asyncio.create_task(_watch_disconnect(request, cancel))
    try:
        transcript = await asyncio.wait_for(
            asyncio.to_thread(
                request.app.state.stt.transcribe,
                decoded.samples,
                sample_rate=decoded.sample_rate,
                language=selected_language,
                model=model_name,
                request_id=request_id,
                cancel=cancel,
            ),
            timeout=settings.stt_timeout_sec,
        )
    except TimeoutError as exc:
        cancel.set()
        raise InferenceTimeout("transcription exceeded the processing deadline") from exc
    finally:
        cancel.set()
        watcher.cancel()
    return TranscriptionResponse(
        text=transcript.text,
        language=transcript.language or selected_language or "und",
        model=transcript.model,
        is_final=transcript.is_final,
        request_id=request_id,
        duration_ms=decoded.duration_ms,
    )


async def _read_bounded(upload: UploadFile, limit: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise AudioTooLarge("audio upload exceeds the configured size limit")
        chunks.append(chunk)
    if total == 0:
        raise InvalidAudio("audio file is empty")
    return b"".join(chunks)


async def _watch_disconnect(request: Request, cancel: threading.Event) -> None:
    try:
        while not cancel.is_set():
            if await request.is_disconnected():
                cancel.set()
                return
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        return


def resolve_request_id(form_value: str | None, header_value: str | None) -> str:
    raw = (form_value or header_value or "").strip()
    if not raw:
        return f"utt_{uuid4().hex[:16]}"
    if not _REQUEST_ID.fullmatch(raw):
        raise InvalidRequest("request_id must be 1-64 letters, numbers, underscores, or hyphens")
    return raw
