from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health/ready")
async def ready(request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    stt = request.app.state.stt.describe()
    tts = request.app.state.tts.describe()
    if not settings.voice_enabled:
        return {
            "status": "not_ready",
            "ready": False,
            "stt": {"available": False, "ready": False, "reason": "voice-disabled"},
            "tts": {"available": False, "ready": False, "reason": "voice-disabled"},
            "realtime": {"available": False, "ready": False, "reason": "not-implemented"},
            "missing": ["stt"],
        }
    is_ready = bool(stt.ready)
    return {
        "status": "ready" if is_ready else "not_ready",
        "ready": is_ready,
        "stt": stt.as_dict(),
        "tts": tts.as_dict(),
        "realtime": {"available": False, "ready": False, "reason": "not-implemented"},
        "missing": [] if is_ready else ["stt"],
    }
