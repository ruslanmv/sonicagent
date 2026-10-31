"""Hugging Face/local ASGI entrypoint, serving the SonicAgent Voice Studio.

Speech inference stays in sonicagent_rt. The UI is static and never embeds a
server-side API token; protected operations keep using Authorization: Bearer.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi.responses import FileResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles

from sonicagent_rt.api.app_factory import create_app
from sonicagent_rt.api.routes.demo import router as demo_router

app = create_app()
app.include_router(demo_router)

UI_DIR = Path(__file__).resolve().parent / "ui"
if UI_DIR.is_dir():
    # The core health router has a JSON GET /. Replace it only for the Space
    # entrypoint. Leave /health/* and /v1/* unchanged.
    app.router.routes[:] = [
        route for route in app.router.routes
        if not (
            isinstance(route, APIRoute)
            and route.path == "/"
            and "GET" in route.methods
        )
    ]
    app.mount("/ui-assets", StaticFiles(directory=UI_DIR), name="voice-studio-assets")

    @app.get("/", include_in_schema=False)
    async def voice_studio():
        return FileResponse(
            UI_DIR / "index.html",
            headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"},
        )

    @app.get("/api-info", include_in_schema=False)
    async def api_info():
        return {
            "service": "sonicagent",
            "live": "/health/live",
            "ready": "/health/ready",
            "capabilities": "/v1/audio/capabilities",
            "ui": "/",
        }


def main() -> None:
    import uvicorn
    port = int(os.environ.get("PORT", "7860"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, workers=1)


if __name__ == "__main__":
    main()
