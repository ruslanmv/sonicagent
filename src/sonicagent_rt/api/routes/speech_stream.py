"""Create a speech-only stream session. The browser receives a resume token, not the API key."""

from __future__ import annotations

import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from sonicagent_rt.auth.service_token import enforce_origin, require_api_key
from sonicagent_rt.speech_stream.store import MODES, OPTION_VALUES, SpeechStreamSession, StreamOptions
from sonicagent_rt.stt.errors import InvalidRequest, VoiceDisabled
from sonicagent_rt.stt.language_detection import normalize_language
from sonicagent_rt.tts.models import validate_voice_id

router = APIRouter(prefix="/audio", tags=["speech-stream"])

_PROVIDERS = {"faster-whisper": "endpointed"}


class StreamSessionCreate(BaseModel):
    mode: str = "stt_only"
    language: str = "en"
    voice_id: str = "en_US-lessac-medium"
    stt_provider: str = "faster-whisper"
    input_audio: dict[str, object] = Field(default_factory=dict)
    # HV3. Optional, negotiated. Absent means sonic-speech-stream-v1 exactly.
    stream_options: dict[str, object] | None = None


@router.post("/stream-sessions")
async def create_stream_session(body: StreamSessionCreate, request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    if not settings.voice_enabled:
        raise VoiceDisabled("voice endpoints are disabled")
    token = require_api_key(request.headers.get("authorization"), settings)
    enforce_origin(request.headers.get("origin"), settings)
    key = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    request.app.state.rate_limiter.check(key)
    mode = body.mode.strip().lower()
    if mode not in MODES:
        raise InvalidRequest("mode must be stt_only, tts_only, or duplex_speech")
    provider = body.stt_provider.strip().lower()
    if provider == "moonshine-streaming":
        raise InvalidRequest("moonshine-streaming is not installed")
    if provider not in _PROVIDERS:
        raise InvalidRequest("stt provider is not available")
    language = normalize_language(body.language, allowed=settings.parsed_stt_languages(), default="en")
    voice_id = validate_voice_id(body.voice_id)
    options = StreamOptions.parse(body.stream_options, default_frame_ms=settings.audio_frame_ms)
    stt = request.app.state.stt.describe()
    tts = request.app.state.tts.describe()
    session_id = f"s_{uuid4().hex}"
    resume = secrets.token_urlsafe(32)
    now = time.monotonic()
    request.app.state.speech_streams.put(
        SpeechStreamSession(
            session_id=session_id,
            resume_token=resume,
            mode=mode,
            language=language,
            voice_id=voice_id,
            stt_provider=provider,
            expires_at=now + settings.session_ttl_sec,
            options=options,
        )
    )
    expires = datetime.now(timezone.utc) + timedelta(seconds=settings.session_ttl_sec)
    partials = bool(settings.stt_partials_enabled) and _PROVIDERS[provider] == "incremental"
    return {
        "session_id": session_id,
        "resume_token": resume,
        "websocket_url": f"/v1/audio/stream/{session_id}",
        "expires_at": expires.isoformat(),
        "protocol": "sonic-speech-stream-v1",
        "mode": mode,
        "llm": False,
        "stt": {
            "provider": provider,
            "streaming": True,
            "streaming_mode": _PROVIDERS[provider],
            "partial_results": partials,
            "ready": bool(stt.ready),
        },
        "tts": {
            "provider": "piper",
            "streaming_audio": True,
            "incremental": "sentence",
            "ready": bool(tts.ready),
        },
        "input_audio": {
            "codec": "pcm_s16le",
            "sample_rate": settings.input_sample_rate,
            "channels": 1,
            "frame_ms": [20, 40],
        },
        "options": options.as_dict(),
        "options_supported": {key: list(values) for key, values in OPTION_VALUES.items()},
    }
