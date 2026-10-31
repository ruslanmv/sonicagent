"""Voice identifiers accepted by optional Piper synthesis."""

from __future__ import annotations

import json
import re
from pathlib import Path

from sonicagent_rt.stt.errors import UnsupportedModel, VoiceUnavailable

_VOICE_ID = re.compile(r"^[a-z]{2}_[A-Z]{2}-[A-Za-z0-9_-]+$")


def validate_voice_id(voice_id: str) -> str:
    if not _VOICE_ID.fullmatch(voice_id):
        raise UnsupportedModel("voice id is not allowed")
    return voice_id


def registry_voice_ids(registry_path: Path | None = None) -> set[str]:
    path = registry_path or _default_registry()
    if path is None or not path.is_file():
        return set()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    voices = payload.get("voices") if isinstance(payload, dict) else None
    if not isinstance(voices, list):
        return set()
    found: set[str] = set()
    for item in voices:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            found.add(item["id"])
    return found


def resolve_voice_files(model_dir: Path, voice_id: str) -> tuple[Path, Path]:
    validate_voice_id(voice_id)
    allowed = registry_voice_ids()
    if allowed and voice_id not in allowed:
        raise VoiceUnavailable("voice is not in the local voice registry")
    candidates = [
        model_dir / f"{voice_id}.onnx",
        model_dir / voice_id / f"{voice_id}.onnx",
    ]
    for model in candidates:
        config = model.with_suffix(".onnx.json")
        if model.is_file() and config.is_file():
            return model, config
    raise VoiceUnavailable("voice model files are not installed")


def _default_registry() -> Path | None:
    candidates = [
        Path.cwd() / "model_registry" / "voices.json",
        Path(__file__).resolve().parents[3] / "model_registry" / "voices.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None
