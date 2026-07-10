from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/health/ready")
async def ready() -> dict[str, object]:
    return {"status": "scaffold", "ready": False, "missing": ["vad", "stt", "tts"]}
