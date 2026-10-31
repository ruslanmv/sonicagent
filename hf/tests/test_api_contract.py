"""OpenAPI and error-envelope contract for the voice routes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from sonicagent_rt.api.app_factory import create_app
from sonicagent_rt.config import Settings


def test_openapi_lists_voice_routes_and_errors_are_structured() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            api_key="c" * 16,
            environment="development",
            auth_mode="development",
            voice_enabled=True,
            stt_warmup=False,
        )
    )
    schema = app.openapi()
    paths = schema["paths"]
    assert "/v1/audio/transcriptions" in paths
    assert "post" in paths["/v1/audio/transcriptions"]
    assert "/v1/audio/capabilities" in paths
    assert "/v1/audio/speech" in paths
    assert "/health/ready" in paths
    with TestClient(app) as client:
        response = client.post("/v1/audio/transcriptions")
    body = response.json()
    assert response.status_code == 401
    assert set(body) == {"error"}
    assert body["error"]["code"] == "unauthenticated"
    assert "message" in body["error"]
