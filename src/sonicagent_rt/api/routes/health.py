from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "sonicagent",
        "live": "/health/live",
        "ready": "/health/ready",
        "capabilities": "/v1/audio/capabilities",
    }


@router.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}
