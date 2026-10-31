"""Speech model identifiers and registry metadata.

English-only checkpoints are rejected while Italian is enabled. Hugging Face
is an optional download mirror; a local ``model.bin`` directory is sufficient
at runtime.
"""

from __future__ import annotations

from pathlib import Path

from sonicagent_rt.stt.errors import UnsupportedModel

# Multilingual CTranslate2 sizes this service is willing to load.
MULTILINGUAL_SIZES = frozenset(
    {"tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3"}
)
SIZE_ALIASES = {
    "large": "large-v3",
    "whisper-large": "large-v3",
}

# Default revision captured from Systran/faster-whisper-tiny when this
# milestone was implemented. setup-models.py uses it so a later upstream
# change cannot silently replace the tested checkpoint.
PINNED_REVISIONS = {
    "tiny": "d90ca5fe260221311c53c58e660288d3deb8d356",
}
PINNED_MODEL_SHA256 = {
    "tiny": "dcb76c6586fc06cbdac6dd21f14cfd129cc4cdd9dce19bf4ffa62e59cbe6e6d1",
}
WHISPER_REPOS = {
    "tiny": "Systran/faster-whisper-tiny",
    "base": "Systran/faster-whisper-base",
    "small": "Systran/faster-whisper-small",
    "medium": "Systran/faster-whisper-medium",
    "large-v1": "Systran/faster-whisper-large-v1",
    "large-v2": "Systran/faster-whisper-large-v2",
    "large-v3": "Systran/faster-whisper-large-v3",
}


def canonical_size(name: str) -> str:
    """Return the faster-whisper size for a public or short model name."""
    raw = name.strip().lower()
    if not raw:
        raise UnsupportedModel("a speech model name is required")
    if raw in SIZE_ALIASES:
        return SIZE_ALIASES[raw]
    if raw.startswith("whisper-"):
        raw = raw[len("whisper-") :]
    if raw in SIZE_ALIASES:
        return SIZE_ALIASES[raw]
    if raw.endswith(".en"):
        raise UnsupportedModel(
            "English-only Whisper models cannot transcribe Italian. Choose tiny, base, or another multilingual model."
        )
    if raw not in MULTILINGUAL_SIZES:
        raise UnsupportedModel("requested speech model is not supported")
    return raw


def public_model_id(name: str) -> str:
    return f"whisper-{canonical_size(name)}"


def registry_file(explicit: str | None = None) -> Path | None:
    """Locate ``model_registry/stt_models.json`` without requiring it to exist."""
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    candidates.append(Path.cwd() / "model_registry" / "stt_models.json")
    candidates.append(Path(__file__).resolve().parents[3] / "model_registry" / "stt_models.json")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def installed_model_dir(cache_dir: str, size: str) -> Path:
    return Path(cache_dir).expanduser() / "stt" / canonical_size(size)


def model_is_installed(cache_dir: str, size: str, explicit_path: str = "") -> bool:
    if explicit_path.strip():
        return (Path(explicit_path).expanduser() / "model.bin").is_file()
    try:
        directory = installed_model_dir(cache_dir, size)
    except UnsupportedModel:
        return False
    return (directory / "model.bin").is_file()
