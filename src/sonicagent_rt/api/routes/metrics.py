from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def metrics() -> Response:
    body = '# SonicAgent metrics scaffold\nsonicagent_build_info{version="0.0.0-dev"} 1\n'
    body += generate_latest().decode("utf-8")
    return Response(content=body, media_type=CONTENT_TYPE_LATEST)
