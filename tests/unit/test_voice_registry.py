"""Each language lists only its own Piper voices. Companion and Secretary stay female."""

import json
from collections import defaultdict
from pathlib import Path

from sonicagent_rt.stt.language_detection import normalize_language
from sonicagent_rt.tts.models import registry_voices, tts_language_supported, validate_voice_id

ROOT = Path(__file__).resolve().parents[2]
OFFERED = {"en-US", "en-GB", "es-ES", "es-MX", "es-AR", "fr-FR", "de-DE", "it-IT", "pt-BR"}


def test_catalog_keeps_roles_and_one_language_per_voice() -> None:
    voices = registry_voices()
    by_locale: dict[str, set[str]] = defaultdict(set)
    ids: set[str] = set()
    for voice in voices:
        validate_voice_id(voice.id)
        # MIT for the Piper voice projects; two speakers carry their dataset's licence and
        # must name who to credit (Serena CC-BY-4.0, Daniela CC-BY-SA-4.0).
        assert voice.license in {"MIT", "CC-BY-4.0", "CC-BY-SA-4.0"}, voice.id
        assert voice.model_path.startswith(("en/", "es/", "fr/", "de/", "it/", "pt/"))
        assert voice.id.startswith(voice.locale.replace("-", "_"))
        if voice.role in {"companion", "secretary"}:
            assert voice.gender == "female"
        else:
            assert voice.role == "catalog"
            assert voice.gender in {"female", "male", "unspecified"}
        by_locale[voice.locale].add(voice.role)
        assert voice.id not in ids
        ids.add(voice.id)
    assert set(by_locale) == OFFERED
    for locale, roles in by_locale.items():
        if locale in {"pt-BR", "es-AR"}:
            assert roles == {"catalog"}, locale
        else:
            assert {"companion", "secretary"} <= roles, locale


def test_companion_is_slower_than_secretary() -> None:
    voices = {voice.id: voice for voice in registry_voices()}
    assert voices["en_US-kristin-medium"].length_scale > voices["en_US-lessac-medium"].length_scale
    assert voices["it_IT-paola-companion"].model_filename == voices["it_IT-paola-medium"].model_filename
    assert voices["es_ES-sharvard-companion"].speaker_id == 1
    assert voices["es_ES-sharvard-secretary"].speaker_id == 1
    assert voices["es_ES-sharvard-male"].speaker_id == 0
    assert voices["es_ES-sharvard-male"].gender == "male"
    assert voices["es_ES-sharvard-male"].model_filename == voices["es_ES-sharvard-secretary"].model_filename
    assert voices["fr_FR-upmc-medium"].speaker_id == 0
    assert voices["fr_FR-upmc-pierre"].speaker_id == 1


def test_italian_and_spanish_do_not_include_english_voices() -> None:
    by_locale: dict[str, set[str]] = defaultdict(set)
    for voice in registry_voices():
        by_locale[voice.locale].add(voice.id)
    italian = by_locale["it-IT"]
    assert italian == {
        "it_IT-paola-companion",
        "it_IT-paola-medium",
        "it_IT-riccardo-x_low",
        "it_IT-serena-medium",
        "it_IT-serena-high",
    }
    assert "en_US-lessac-medium" not in italian
    spanish = by_locale["es-ES"] | by_locale["es-MX"] | by_locale["es-AR"]
    assert by_locale["es-AR"] == {"es_AR-daniela-high"}
    assert "en_US-lessac-medium" not in spanish
    assert "es_ES-sharvard-male" in by_locale["es-ES"]
    assert "es_ES-davefx-medium" in by_locale["es-ES"]
    assert "es_MX-claude-high" in by_locale["es-MX"]


def test_portuguese_voices_are_labeled_male() -> None:
    assert normalize_language("pt-BR", allowed=["en", "es", "fr", "de", "it", "pt"], default="auto") == "pt"
    assert tts_language_supported("pt") is True
    assert tts_language_supported("pt-BR") is True
    assert tts_language_supported("it-IT") is True
    assert tts_language_supported("es-ES") is True
    portuguese = [voice for voice in registry_voices() if voice.language == "pt"]
    assert {voice.id for voice in portuguese} == {"pt_BR-edresson-low", "pt_BR-faber-medium"}
    assert all(voice.gender == "male" for voice in portuguese)


def test_studio_catalog_matches_the_registry_by_language() -> None:
    catalog = json.loads((ROOT / "hf" / "ui" / "catalog.json").read_text(encoding="utf-8"))
    script = (ROOT / "hf" / "ui" / "app.js").read_text(encoding="utf-8")
    assert 'fetch("/ui-assets/catalog.json"' in script
    assert "return voices[E.ttsLanguage.value] || [];" in script
    assert 'voices[lang] || voices["en-US"]' not in script
    ui: dict[str, set[str]] = {}
    for locale in catalog["locales"]:
        ids = {voice["id"] for voice in locale["voices"]}
        assert ids
        for voice_id in ids:
            assert voice_id.startswith(locale["id"].replace("-", "_"))
        ui[locale["id"]] = ids
    registry: dict[str, set[str]] = defaultdict(set)
    for voice in registry_voices():
        registry[voice.locale].add(voice.id)
    assert ui == dict(registry)
    assert "en_US-lessac-medium" not in ui["it-IT"]
    assert "en_US-lessac-medium" not in ui["es-ES"]


def test_every_non_mit_voice_names_whom_to_credit() -> None:
    import json
    from pathlib import Path

    registry = Path(__file__).resolve().parents[2] / "model_registry" / "voices.json"
    for entry in json.loads(registry.read_text(encoding="utf-8"))["voices"]:
        if entry["license"] != "MIT":
            assert entry.get("attribution"), entry["id"]
            assert len(entry["model_sha256"]) == 64 and len(entry["config_sha256"]) == 64, entry["id"]
