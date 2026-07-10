from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi import APIRouter
from pydantic import BaseModel, Field

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
async def create_session(request: SessionCreate) -> dict[str, object]:
    session_id = f"ses_{uuid4().hex}"
    return {
        "session_id": session_id,
        "resume_token": "development-token",
        "websocket_url": f"/v1/realtime/{session_id}",
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
        "server_capabilities": {"binary_audio": True, "barge_in": True, "partial_transcripts": False, "phrase_pipelined_tts": True},
        "output_audio": {"codec": "pcm_s16le", "sample_rate": 22050, "channels": 1},
        "warning": "Scaffold response; replace the in-memory session implementation before production.",
    }
