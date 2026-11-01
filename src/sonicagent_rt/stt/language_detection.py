"""Normalize caller language selections for multilingual Whisper."""

from __future__ import annotations

from sonicagent_rt.stt.errors import UnsupportedLanguage

_ALIASES = {
    "en": "en",
    "en-us": "en",
    "en-gb": "en",
    "english": "en",
    "es": "es",
    "es-es": "es",
    "es-mx": "es",
    "spanish": "es",
    "espanol": "es",
    "español": "es",
    "fr": "fr",
    "fr-fr": "fr",
    "french": "fr",
    "francais": "fr",
    "français": "fr",
    "de": "de",
    "de-de": "de",
    "german": "de",
    "deutsch": "de",
    "it": "it",
    "it-it": "it",
    "italian": "it",
    "italiano": "it",
    "pt": "pt",
    "pt-br": "pt",
    "pt-pt": "pt",
    "portuguese": "pt",
    "portugues": "pt",
    "português": "pt",
}


def normalize_language(value: str | None, *, allowed: list[str], default: str) -> str | None:
    """Return a Whisper language code, or ``None`` when detection is requested.

    ``auto`` lets the model detect the spoken language. Explicit codes must be
    in the configured allow-list. This function does not translate audio.
    """
    raw = (value if value is not None and value.strip() else default).strip().lower().replace("_", "-")
    if raw in {"", "auto", "detect"}:
        return None
    code = _ALIASES.get(raw)
    allowed_codes = {item.lower() for item in allowed}
    if code is None or code not in allowed_codes:
        names = ", ".join(item.lower() for item in allowed)
        raise UnsupportedLanguage(f"language must be {names}, or auto")
    return code
