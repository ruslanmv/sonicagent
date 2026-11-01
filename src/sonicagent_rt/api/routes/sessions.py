"""Create a short-lived realtime session. The resume token is the websocket credential."""

import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from sonicagent_rt.auth.service_token import enforce_origin, require_api_key
from sonicagent_rt.stt.errors import VoiceDisabled

router = APIRouter(prefix="/sessions", tags=["sessions"])


class AudioFormat(BaseModel):
    codec: str = "pcm_s16le"
    sample_rate: int = 16000
    channels: int = 1
    frame_ms: int = 20


class SessionCreate(BaseModel):
    language: str = "en"
    voice_id: str = "en_US-lessac-medium"
    input_audio: AudioFormat = Field(default_factory=AudioFormat)
    client_capabilities: dict[str, bool] = Field(default_factory=dict)


@router.post("")
async def create_session(body: SessionCreate, request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    if not settings.voice_enabled:
        raise VoiceDisabled("voice endpoints are disabled")
    token = require_api_key(request.headers.get("authorization"), settings)
    enforce_origin(request.headers.get("origin"), settings)
    key = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    request.app.state.rate_limiter.check(key)
    session = request.app.state.sessions.create(language=body.language, voice_id=body.voice_id)
    tts = request.app.state.tts.describe()
    expires = datetime.now(timezone.utc) + timedelta(seconds=settings.session_ttl_sec)
    return {
        "session_id": session.session_id,
        "resume_token": session.resume_token,
        "websocket_url": f"/v1/realtime/{session.session_id}",
        "expires_at": expires.isoformat(),
        "server_capabilities": {
            "binary_audio": True,
            "barge_in": settings.barge_in_enabled,
            "partial_transcripts": False,
            "phrase_pipelined_tts": bool(tts.ready),
        },
        "output_audio": {"codec": "pcm_s16le", "sample_rate": 22050, "channels": 1},
    }
