"""The voice catalog lists every Piper id the server can select."""

from pathlib import Path

from sonicagent_rt.tts.models import voice_catalog
from tests.unit.test_voice_api import FakeStt, client_for, settings

ROOT = Path(__file__).resolve().parents[2]


def test_catalog_document_names_every_registered_voice() -> None:
    catalog = voice_catalog()
    text = (ROOT / "catalog" / "README.md").read_text(encoding="utf-8")
    assert catalog["voice_count"] == 52
    assert catalog["model_file_count"] == 47
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
    assert body["voice_count"] == 52
    assert body["installed_count"] == 0
    assert body["styles"]["companion"]["length_scale"] == 1.16
    ids = {voice["id"] for voice in body["voices"]}
    assert "en_US-kristin-medium" in ids
    assert "it_IT-paola-companion" in ids
    assert "pt_BR-faber-medium" in ids
    assert all(voice["installed"] is False for voice in body["voices"])


def test_serena_and_daniela_are_registered_with_their_own_licences() -> None:
    voices = {voice["id"]: voice for voice in voice_catalog()["voices"]}
    for voice_id in ("it_IT-serena-medium", "it_IT-serena-high"):
        serena = voices[voice_id]
        assert (serena["gender"], serena["locale"], serena["role"]) == ("female", "it-IT", "catalog")
        assert serena["license"] == "CC-BY-4.0"
    daniela = voices["es_AR-daniela-high"]
    assert (daniela["gender"], daniela["locale"], daniela["license"]) == ("female", "es-AR", "CC-BY-SA-4.0")
    # Paola is still the Italian companion and secretary.
    assert voices["it_IT-paola-companion"]["role"] == "companion"
    assert voices["it_IT-paola-medium"]["role"] == "secretary"


def test_a_scale_written_on_a_voice_wins_over_its_role_style() -> None:
    voices = {voice["id"]: voice for voice in voice_catalog()["voices"]}
    serena = voices["it_IT-serena-medium"]
    assert (serena["length_scale"], serena["noise_scale"], serena["noise_w_scale"]) == (1.0, 0.6, 0.4)
    # Voices without their own scales keep the role style.
    daniela = voices["es_AR-daniela-high"]
    assert (daniela["noise_scale"], daniela["noise_w_scale"]) == (0.667, 0.8)
    assert voices["it_IT-paola-companion"]["length_scale"] == 1.16


def test_an_out_of_range_voice_scale_is_ignored() -> None:
    from sonicagent_rt.tts.models import _voice_style

    role = {"length_scale": 1.0, "noise_scale": 0.667, "noise_w_scale": 0.8}
    assert _voice_style({"noise_scale": 9, "noise_w_scale": True}, role) == role
