"""Normalize caller language selections for multilingual Whisper."""

from __future__ import annotations

from sonicagent_rt.stt.errors import UnsupportedLanguage

_ALIASES = {
    "en": "en",
    "en-us": "en",
    "en-gb": "en",
    "english": "en",
    "it": "it",
    "it-it": "it",
    "italian": "it",
    "italiano": "it",
}


def normalize_language(value: str | None, *, allowed: list[str], default: str) -> str | None:
    """Return a Whisper language code, or ``None`` when detection is requested.

    ``auto`` lets the model detect the spoken language. Explicit codes must be
    in the configured allow-list. This function does not translate audio.
    """
    raw = (value if value is not None and value.strip() else default).strip().lower()
    if raw in {"", "auto", "detect"}:
        return None
    code = _ALIASES.get(raw)
    if code is None or code not in {item.lower() for item in allowed}:
        raise UnsupportedLanguage("language must be en, it, or auto")
    return code
