"""FastAPI application factory."""
from fastapi import FastAPI
from sonicagent_rt.version import __version__
from .routes import health, readiness, sessions, voices, models, metrics
from .websocket.endpoint import router as websocket_router

def create_app() -> FastAPI:
    app = FastAPI(title="SonicAgent", version=__version__)
    app.include_router(health.router)
    app.include_router(readiness.router)
    app.include_router(sessions.router, prefix="/v1")
    app.include_router(voices.router, prefix="/v1")
    app.include_router(models.router, prefix="/v1")
    app.include_router(metrics.router)
    app.include_router(websocket_router, prefix="/v1")
    return app
