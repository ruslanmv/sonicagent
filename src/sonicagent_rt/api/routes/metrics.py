from fastapi import APIRouter, Response

router = APIRouter(tags=["metrics"])

@router.get("/metrics", response_class=Response)
async def metrics() -> str:
    return "# SonicAgent metrics scaffold\nsonicagent_build_info{version=\"0.0.0-dev\"} 1\n"
