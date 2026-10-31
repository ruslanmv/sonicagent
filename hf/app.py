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
def _prefer_route(path: str) -> None:
    """Match a Space route before included routers.

    Current FastAPI keeps included routers as ``_IncludedRouter`` objects, so
    filtering only top-level ``APIRoute`` entries leaves the JSON ``GET /``
    from the health router in front of the Voice Studio page.
    """
    chosen = [
        route
        for route in app.router.routes
        if isinstance(route, APIRoute) and route.path == path and "GET" in route.methods
    ]
    if not chosen:
        return
    rest = [route for route in app.router.routes if route not in chosen]
    app.router.routes[:] = [*chosen, *rest]


if UI_DIR.is_dir():
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

    _prefer_route("/")


def main() -> None:
    import uvicorn
    port = int(os.environ.get("PORT", "7860"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, workers=1)


if __name__ == "__main__":
    main()
