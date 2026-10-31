"""The Space entrypoint serves SonicAgent rather than a hello-world app."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient


def _load_app():
    path = Path(__file__).resolve().parents[1] / "app.py"
    spec = importlib.util.spec_from_file_location("sonicagent_hf_app", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


def test_space_app_exposes_health_and_transcription() -> None:
    app = _load_app()
    # FastAPI 0.116+ keeps included routers lazy until the OpenAPI schema is built.
    paths = set(app.openapi()["paths"])
    assert "/health/live" in paths
    assert "/health/ready" in paths
    assert "/v1/audio/transcriptions" in paths
    assert "/v1/audio/capabilities" in paths
    assert "/v1/audio/speech" in paths
    with TestClient(app) as client:
        live = client.get("/health/live")
        ready = client.get("/health/ready")
    assert live.status_code == 200
    assert live.json()["status"] == "ok"
    assert ready.json()["ready"] in {True, False}
    assert "text" not in ready.json()
