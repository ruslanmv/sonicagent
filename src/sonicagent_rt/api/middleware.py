"""Request guards that run before a microphone upload is parsed."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def install_upload_limit(app: FastAPI) -> None:
    @app.middleware("http")
    async def limit_audio_upload(request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.method == "POST" and request.url.path == "/v1/audio/transcriptions":
            raw = request.headers.get("content-length")
            if raw is not None:
                try:
                    size = int(raw)
                except ValueError:
                    return JSONResponse(
                        status_code=400,
                        content={"error": {"code": "invalid_request", "message": "content length is invalid"}},
                        headers={"Cache-Control": "no-store"},
                    )
                settings = request.app.state.settings
                if size > int(settings.max_upload_bytes) + 65536:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": {
                                "code": "audio_too_large",
                                "message": "audio upload exceeds the configured size limit",
                            }
                        },
                        headers={"Cache-Control": "no-store"},
                    )
        return await call_next(request)
