"""JSON error responses for the voice API."""

from __future__ import annotations

from fastapi.responses import JSONResponse

from sonicagent_rt.stt.errors import SpeechError


def error_response(exc: SpeechError, request_id: str | None) -> JSONResponse:
    body: dict[str, object] = {"code": exc.code, "message": exc.message}
    if request_id:
        body["request_id"] = request_id
    headers = {"Cache-Control": "no-store"}
    if exc.status_code in {429, 503}:
        headers["Retry-After"] = "5"
    return JSONResponse(status_code=exc.status_code, content={"error": body}, headers=headers)
