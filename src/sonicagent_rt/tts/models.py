"""Voice identifiers accepted by optional Piper synthesis."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from sonicagent_rt.stt.errors import UnsupportedModel, VoiceUnavailable

_VOICE_ID = re.compile(r"^[a-z]{2}_[A-Z]{2}-[A-Za-z0-9_-]+$")
_DEFAULT_STYLES = {
    "companion": {"length_scale": 1.16, "noise_scale": 0.8, "noise_w_scale": 0.92},
    "secretary": {"length_scale": 0.94, "noise_scale": 0.48, "noise_w_scale": 0.6},
    "catalog": {"length_scale": 1.0, "noise_scale": 0.667, "noise_w_scale": 0.8},
}


@dataclass(frozen=True)
class VoiceRecord:
    id: str
    display_name: str
    role: str
    gender: str
    language: str
    locale: str
    language_label: str
    quality: str
    speaker_id: int | None
    length_scale: float
    noise_scale: float
    noise_w_scale: float
    model_path: str
    config_path: str
    license: str

    @property
    def model_filename(self) -> str:
        return Path(self.model_path).name

    @property
    def config_filename(self) -> str:
        return Path(self.config_path).name


def validate_voice_id(voice_id: str) -> str:
    if not _VOICE_ID.fullmatch(voice_id):
        raise UnsupportedModel("voice id is not allowed")
    return voice_id


def registry_voices(registry_path: Path | None = None) -> tuple[VoiceRecord, ...]:
    path = registry_path or _default_registry()
    if path is None or not path.is_file():
        return ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ()
    if not isinstance(payload, dict):
        return ()
    styles = payload.get("styles") if isinstance(payload.get("styles"), dict) else {}
    voices = payload.get("voices")
    if not isinstance(voices, list):
        return ()
    records: list[VoiceRecord] = []
    for item in voices:
        record = _record(item, styles)
        if record is not None:
            records.append(record)
    return tuple(records)


def registry_voice_ids(registry_path: Path | None = None) -> set[str]:
    return {record.id for record in registry_voices(registry_path)}


def voice_record(voice_id: str, registry_path: Path | None = None) -> VoiceRecord | None:
    for record in registry_voices(registry_path):
        if record.id == voice_id:
            return record
    return None


def tts_language_supported(language: str, registry_path: Path | None = None) -> bool:
    raw = language.strip().lower().replace("_", "-")
    if not raw:
        return False
    for record in registry_voices(registry_path):
        if raw == record.language or raw == record.locale.lower():
            return True
    return False


def resolve_voice_files(model_dir: Path, voice_id: str) -> tuple[Path, Path]:
    validate_voice_id(voice_id)
    record = voice_record(voice_id)
    if record is None:
        raise VoiceUnavailable("voice is not in the local voice registry")
    candidates = [
        model_dir / record.model_filename,
        model_dir / voice_id / record.model_filename,
    ]
    for model in candidates:
        config = model.with_name(record.config_filename)
        if model.is_file() and config.is_file():
            return model, config
    raise VoiceUnavailable("voice model files are not installed")


def _record(item: object, styles: dict[str, object]) -> VoiceRecord | None:
    if not isinstance(item, dict) or not isinstance(item.get("id"), str):
        return None
    if not isinstance(item.get("model_path"), str) or not isinstance(item.get("config_path"), str):
        return None
    role = str(item.get("role") or "secretary")
    style = _style(styles, role)
    speaker = item.get("speaker_id")
    speaker_id = speaker if isinstance(speaker, int) else None
    return VoiceRecord(
        id=item["id"],
        display_name=str(item.get("display_name") or item["id"]),
        role=role,
        gender=str(item.get("gender") or "female"),
        language=str(item.get("language") or ""),
        locale=str(item.get("locale") or ""),
        language_label=str(item.get("language_label") or item.get("language") or ""),
        quality=str(item.get("quality") or ""),
        speaker_id=speaker_id,
        length_scale=float(style["length_scale"]),
        noise_scale=float(style["noise_scale"]),
        noise_w_scale=float(style["noise_w_scale"]),
        model_path=item["model_path"],
        config_path=item["config_path"],
        license=str(item.get("license") or ""),
    )


def _style(styles: dict[str, object], role: str) -> dict[str, float]:
    raw = styles.get(role)
    base = dict(_DEFAULT_STYLES.get(role, _DEFAULT_STYLES["secretary"]))
    if isinstance(raw, dict):
        for key in ("length_scale", "noise_scale", "noise_w_scale"):
            value = raw.get(key)
            if isinstance(value, (int, float)):
                base[key] = float(value)
    return base


def _default_registry() -> Path | None:
    here = Path(__file__).resolve()
    candidates = [
        Path.cwd() / "model_registry" / "voices.json",
        here.parents[3] / "model_registry" / "voices.json" if len(here.parents) > 3 else None,
        here.parents[2] / "model_registry" / "voices.json" if len(here.parents) > 2 else None,
    ]
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return candidate
    return None
