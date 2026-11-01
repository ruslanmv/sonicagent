"""List the Piper voices this server can select."""

from fastapi import APIRouter, Request

from sonicagent_rt.tts.models import voice_catalog

router = APIRouter(prefix="/voices", tags=["models"])


@router.get("")
async def list_voices(request: Request) -> dict[str, object]:
    catalog = voice_catalog()
    described = request.app.state.tts.describe()
    installed = set(described.voices)
    voices = []
    for voice in catalog["voices"]:
        if isinstance(voice, dict):
            item = dict(voice)
            item["installed"] = item["id"] in installed
            voices.append(item)
    catalog["voices"] = voices
    catalog["installed_count"] = sum(1 for voice in voices if voice["installed"])
    return catalog
