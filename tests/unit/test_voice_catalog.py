"""The voice catalog lists every Piper id the server can select."""

from pathlib import Path

from sonicagent_rt.tts.models import voice_catalog
from tests.unit.test_voice_api import FakeStt, client_for, settings

ROOT = Path(__file__).resolve().parents[2]


def test_catalog_document_names_every_registered_voice() -> None:
    catalog = voice_catalog()
    text = (ROOT / "catalog" / "README.md").read_text(encoding="utf-8")
    assert catalog["voice_count"] == 49
    assert catalog["model_file_count"] == 44
    assert catalog["status"] == "ready"
    for voice in catalog["voices"]:
        assert f"`{voice['id']}`" in text
    assert "fan-service" in text
    assert "Secretary" in text
    assert "not available to download today" in text


def test_voices_route_returns_the_registry() -> None:
    with client_for(settings(), FakeStt()) as client:
        response = client.get("/v1/voices")
    assert response.status_code == 200
    body = response.json()
    assert body["voice_count"] == 49
    assert body["installed_count"] == 0
    assert body["styles"]["companion"]["length_scale"] == 1.16
    ids = {voice["id"] for voice in body["voices"]}
    assert "en_US-kristin-medium" in ids
    assert "it_IT-paola-companion" in ids
    assert "pt_BR-faber-medium" in ids
    assert all(voice["installed"] is False for voice in body["voices"])
