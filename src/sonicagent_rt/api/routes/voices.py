"""List the Piper voices this server can select, and warm one ahead of use (HV9).

``GET /v1/voices`` is the whole library from ``model_registry/voices.json`` — every voice, with
its language, locale, gender, quality, speaker id and the synthesis settings of its role — plus
what THIS server can do with each one right now:

  ``installed``  the model files are here (unchanged field)
  ``state``      ``loaded`` (in memory: no cold start), ``installed`` (first use loads it),
                 or ``missing`` (not on this server)
  ``playable``   installed AND Piper is ready. Only a playable voice should be offered as
                 selectable; the rest are listed so a person can see what exists.
  ``model_key``  voices with the same key are one ONNX model with different settings or
                 speaker ids, and load once (``shares_model_with`` names the others)

``presets`` names the documented Companion and Secretary voice per locale. Locales the registry
has no female voice for (Brazilian Portuguese today: Edresson and Faber are male) get no
preset — a preset is never invented to fill the table.

``POST /v1/voices/warm`` loads one voice's model before its first sentence. It needs the
service key like every audio route, so an anonymous caller cannot make the server load models.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from sonicagent_rt.api.routes.audio import require_audio_access
from sonicagent_rt.stt.errors import VoiceUnavailable
from sonicagent_rt.tts.models import validate_voice_id, voice_catalog, voice_record

router = APIRouter(prefix="/voices", tags=["models"])

#: The documented presets (hp-piper-voices README, HV9). Each must exist in the registry with
#: this role; a test reads the registry to keep the two in step.
PRESETS: dict[str, dict[str, str]] = {
    "en-US": {"companion": "en_US-kristin-medium", "secretary": "en_US-lessac-medium"},
    "en-GB": {"companion": "en_GB-cori-medium", "secretary": "en_GB-alba-medium"},
    "es-ES": {"companion": "es_ES-sharvard-companion", "secretary": "es_ES-sharvard-secretary"},
    "es-MX": {"companion": "es_MX-ald-companion", "secretary": "es_MX-ald-medium"},
    "fr-FR": {"companion": "fr_FR-upmc-medium", "secretary": "fr_FR-siwis-medium"},
    "de-DE": {"companion": "de_DE-eva_k-x_low", "secretary": "de_DE-kerstin-low"},
    "it-IT": {"companion": "it_IT-paola-companion", "secretary": "it_IT-paola-medium"},
}


def _state(tts: object, voice_id: str, installed: bool) -> str:
    if not installed:
        return "missing"
    is_loaded = getattr(tts, "is_loaded", None)
    try:
        if callable(is_loaded) and is_loaded(voice_id):
            return "loaded"
    except Exception:  # noqa: BLE001 — a status probe never fails the listing
        pass
    return "installed"


@router.get("")
async def list_voices(request: Request) -> dict[str, object]:
    catalog = voice_catalog()
    tts = request.app.state.tts
    described = tts.describe()
    installed = set(described.voices)
    ready = bool(described.ready)
    by_model: dict[str, list[str]] = {}
    for voice in catalog["voices"]:
        if isinstance(voice, dict):
            by_model.setdefault(str(voice.get("model_path")), []).append(str(voice["id"]))
    voices = []
    for voice in catalog["voices"]:
        if isinstance(voice, dict):
            item = dict(voice)
            vid = str(item["id"])
            item["installed"] = vid in installed
            item["state"] = _state(tts, vid, item["installed"])
            item["playable"] = bool(item["installed"] and ready)
            key = str(item.get("model_path"))
            item["model_key"] = key
            item["shares_model_with"] = [other for other in by_model.get(key, []) if other != vid]
            voices.append(item)
    catalog["voices"] = voices
    catalog["installed_count"] = sum(1 for voice in voices if voice["installed"])
    catalog["tts_ready"] = ready
    catalog["presets"] = {
        locale: {role: vid for role, vid in roles.items() if any(v["id"] == vid for v in voices)}
        for locale, roles in PRESETS.items()
    }
    return catalog


class WarmBody(BaseModel):
    voice_id: str


@router.post("/warm")
async def warm_voice(
    body: WarmBody, request: Request, _: None = Depends(require_audio_access)
) -> dict[str, object]:
    voice_id = validate_voice_id(body.voice_id.strip())
    if voice_record(voice_id) is None:
        raise VoiceUnavailable("voice is not in the local voice registry")
    tts = request.app.state.tts
    warm = getattr(tts, "warm", None)
    if not callable(warm):
        raise VoiceUnavailable("this speech engine cannot preload voices")
    # Loading is seconds of CPU: off the event loop, so other sockets keep flowing.
    return await asyncio.to_thread(warm, voice_id)
