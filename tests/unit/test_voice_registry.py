"""The Hugging Face voice catalog is female, and every offered language has both roles."""

from collections import defaultdict

from sonicagent_rt.stt.language_detection import normalize_language
from sonicagent_rt.tts.models import registry_voices, tts_language_supported, validate_voice_id

OFFERED = {"en-US", "en-GB", "es-ES", "es-MX", "fr-FR", "de-DE", "it-IT"}


def test_catalog_is_female_with_companion_and_secretary() -> None:
    voices = registry_voices()
    by_locale: dict[str, set[str]] = defaultdict(set)
    ids: set[str] = set()
    for voice in voices:
        validate_voice_id(voice.id)
        assert voice.gender == "female"
        assert voice.role in {"companion", "secretary"}
        assert voice.license == "MIT"
        assert voice.model_path.startswith(("en/", "es/", "fr/", "de/", "it/"))
        by_locale[voice.locale].add(voice.role)
        assert voice.id not in ids
        ids.add(voice.id)
    assert set(by_locale) == OFFERED
    for locale, roles in by_locale.items():
        assert roles == {"companion", "secretary"}, locale


def test_companion_is_slower_than_secretary() -> None:
    voices = {voice.id: voice for voice in registry_voices()}
    assert voices["en_US-kristin-medium"].length_scale > voices["en_US-lessac-medium"].length_scale
    assert voices["it_IT-paola-companion"].model_filename == voices["it_IT-paola-medium"].model_filename
    assert voices["es_ES-sharvard-companion"].speaker_id == 1
    assert voices["es_ES-sharvard-secretary"].speaker_id == 1
    assert voices["fr_FR-upmc-medium"].speaker_id == 0


def test_portuguese_listening_has_no_female_piper_voice() -> None:
    assert normalize_language("pt-BR", allowed=["en", "es", "fr", "de", "it", "pt"], default="auto") == "pt"
    assert tts_language_supported("pt") is False
    assert tts_language_supported("pt-BR") is False
    assert tts_language_supported("es-ES") is True
    assert all(voice.language != "pt" for voice in registry_voices())


def test_studio_lists_every_catalog_voice() -> None:
    script = (
        __import__("pathlib").Path(__file__).resolve().parents[2] / "hf" / "ui" / "app.js"
    ).read_text(encoding="utf-8")
    for voice in registry_voices():
        assert voice.id in script
        assert voice.locale in script
