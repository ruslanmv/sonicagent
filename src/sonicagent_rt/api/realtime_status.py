"""Honest realtime capability. Ready follows the loaded speech model."""

from __future__ import annotations

from sonicagent_rt.config import Settings
from sonicagent_rt.vad.factory import vad_backend


def realtime_status(settings: Settings, stt: object) -> dict[str, object]:
    if not settings.voice_enabled:
        return {"available": False, "ready": False, "reason": "voice-disabled"}
    available = bool(getattr(stt, "available", False))
    ready = bool(available and getattr(stt, "ready", False))
    reason = None if ready else (getattr(stt, "reason", None) or "model-not-loaded")
    return {
        "available": True,
        "ready": ready,
        "reason": reason,
        "vad": vad_backend(settings),
        "llm": settings.llm_provider,
        "barge_in": settings.barge_in_enabled,
    }
