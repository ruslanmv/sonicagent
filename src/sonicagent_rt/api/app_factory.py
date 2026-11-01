"""FastAPI application factory."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from sonicagent_rt.api.errors import error_response
from sonicagent_rt.api.middleware import install_upload_limit
from sonicagent_rt.api.routes import health, metrics, models, readiness, sessions, voices
from sonicagent_rt.api.routes.audio import InFlightRequests, router as audio_router
from sonicagent_rt.api.websocket.endpoint import router as websocket_router
from sonicagent_rt.config import Settings, get_settings
from sonicagent_rt.lifespan import app_lifespan
from sonicagent_rt.llm.factory import create_llm
from sonicagent_rt.security.rate_limits import SlidingWindowLimiter
from sonicagent_rt.sessions.manager import SessionManager
from sonicagent_rt.stt.errors import SpeechError
from sonicagent_rt.stt.factory import create_stt_engine
from sonicagent_rt.tts.factory import create_tts_engine
from sonicagent_rt.version import __version__


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings if settings is not None else get_settings()
    app = FastAPI(title="SonicAgent", version=__version__, lifespan=app_lifespan)
    app.state.settings = resolved
    app.state.stt = create_stt_engine(resolved)
    app.state.tts = create_tts_engine(resolved)
    app.state.llm = create_llm(resolved)
    app.state.sessions = SessionManager(resolved)
    app.state.rate_limiter = SlidingWindowLimiter(resolved.stt_rate_limit_per_minute)
    app.state.inflight = InFlightRequests()

    @app.exception_handler(SpeechError)
    async def handle_speech_error(request: Request, exc: SpeechError):
        request_id = request.headers.get("x-request-id")
        return error_response(exc, request_id if request_id else None)

    origins = resolved.parsed_allowed_origins()
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
            max_age=600,
        )
    install_upload_limit(app)
    app.include_router(health.router)
    app.include_router(readiness.router)
    app.include_router(sessions.router, prefix="/v1")
    app.include_router(voices.router, prefix="/v1")
    app.include_router(models.router, prefix="/v1")
    app.include_router(audio_router, prefix="/v1")
    app.include_router(metrics.router)
    app.include_router(websocket_router, prefix="/v1")
    return app
