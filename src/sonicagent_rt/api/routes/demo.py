"""Opt-in, rate-limited anonymous Voice Studio demonstration.

The production API continues to require SONIC_API_KEY. Public inference is
off unless an operator explicitly sets SONIC_PUBLIC_DEMO_ENABLED=true.
This is a small demo, not an internet-scale abuse-prevention system.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict, deque
import copy
import os
from threading import Event, Lock
import time
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from sonicagent_rt.api.errors import error_response
from sonicagent_rt.api.routes.audio import _transcription_body
from sonicagent_rt.stt.errors import SpeechError
from sonicagent_rt.tts.models import tts_language_supported

router = APIRouter(tags=["public-demo"])
DEMO_SECONDS = 8.0
DEMO_BYTES = 1_200_000
DEMO_TEXT_CHARS = 180


def _true(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"true", "1", "yes", "on"}


def _enabled() -> bool:
    return _true("SONIC_PUBLIC_DEMO_ENABLED")


def _tts_enabled() -> bool:
    return _enabled() and _true("SONIC_PUBLIC_DEMO_TTS_ENABLED")


class DemoRateLimiter:
    """In-process maximum of 8 total and 3 per client requests/minute.

    Per-client addresses are advisory behind a reverse proxy; the global cap
    still protects a single-worker Space. Do not treat this as a bot firewall.
    """
    def __init__(self, total_per_minute: int = 8, per_client_minute: int = 3):
        self.total = deque()
        self.clients = defaultdict(deque)
        self.lock = Lock()
        self.total_per_minute = total_per_minute
        self.per_client_minute = per_client_minute

    def check(self, client: str) -> None:
        with self.lock:
            now = time.monotonic()
            while self.total and now - self.total[0] >= 60:
                self.total.popleft()
            bucket = self.clients[client]
            while bucket and now - bucket[0] >= 60:
                bucket.popleft()
            if len(self.total) >= self.total_per_minute or len(bucket) >= self.per_client_minute:
                raise HTTPException(429, "Demo limit reached. Try again in a minute.",
                                    headers={"Retry-After": "60"})
            self.total.append(now)
            bucket.append(now)


limiter = DemoRateLimiter()
slot = asyncio.Semaphore(1)


def _check(request: Request) -> None:
    if not _enabled():
        raise HTTPException(404, "Public demo is disabled")
    # These headers discourage accidental cross-site use but are not proof of identity.
    if request.headers.get("x-sonic-demo-ui") != "1":
        raise HTTPException(403, "Use the Voice Studio demo")
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Cross-site requests are disabled")
    origin = request.headers.get("origin")
    if origin:
        parsed = urlparse(origin)
        if parsed.scheme not in {"http", "https"} or parsed.netloc != request.headers.get("host"):
            raise HTTPException(403, "Cross-origin requests are disabled")
    limiter.check(request.client.host if request.client else "unknown")


@router.get("/demo/status")
async def status(request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    stt = request.app.state.stt.describe()
    tts = request.app.state.tts.describe()
    return {
        "enabled": _enabled(),
        "tts_enabled": _tts_enabled() and bool(tts.ready),
        "stt_ready": bool(stt.ready),
        "max_audio_seconds": min(DEMO_SECONDS, settings.max_audio_seconds),
        "max_upload_bytes": min(DEMO_BYTES, settings.max_upload_bytes),
    }


@router.post("/demo/transcriptions")
async def transcription(
    request: Request,
    file: UploadFile = File(...),
    language: str | None = Form(default=None),
):
    _check(request)
    settings = copy.copy(request.app.state.settings)
    settings.max_audio_seconds = min(DEMO_SECONDS, settings.max_audio_seconds)
    settings.max_upload_bytes = min(DEMO_BYTES, settings.max_upload_bytes)
    request_id = "demo_" + uuid4().hex[:20]
    try:
        async with slot:
            result = await _transcription_body(
                request, settings, file=file, language=language, model=None,
                request_id=request_id,
            )
        return JSONResponse(result.model_dump(), headers={"Cache-Control": "no-store"})
    except SpeechError as exc:
        return error_response(exc, request_id)
    except Exception:
        return JSONResponse(
            status_code=503, content={"error": {"message": "Demo STT unavailable"}},
            headers={"Cache-Control": "no-store"},
        )


class DemoSpeechRequest(BaseModel):
    text: str
    voice: str | None = None
    language: str = "en"
    format: str = "wav"


@router.post("/demo/speech")
async def speech(request: Request, body: DemoSpeechRequest):
    _check(request)
    if not _tts_enabled() or not request.app.state.tts.describe().ready:
        raise HTTPException(503, "Public Piper synthesis is disabled")
    if not body.text.strip() or len(body.text) > DEMO_TEXT_CHARS:
        raise HTTPException(422, "Text must contain 1–180 characters")
    if body.format != "wav" or not tts_language_supported(body.language):
        raise HTTPException(422, "Unsupported language or format")
    settings = request.app.state.settings
    cancel = Event()
    try:
        async with slot:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    request.app.state.tts.synthesize,
                    body.text,
                    voice=body.voice or settings.tts_voice,
                    language=body.language,
                    cancel=cancel,
                ),
                timeout=min(settings.tts_timeout_sec, 30),
            )
        return Response(
            result.wav, media_type="audio/wav",
            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )
    except Exception:
        cancel.set()
        return JSONResponse(
            status_code=503, content={"error": {"message": "Piper unavailable"}},
            headers={"Cache-Control": "no-store"},
        )
