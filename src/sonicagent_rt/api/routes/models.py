import json

from fastapi import APIRouter, Request

from sonicagent_rt.stt.models import canonical_size, model_is_installed, public_model_id, registry_file

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/stt")
async def list_stt_models(request: Request) -> dict[str, object]:
    path = registry_file()
    if path is None:
        return {"models": [], "status": "unavailable"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"models": [], "status": "unavailable"}
    settings = request.app.state.settings
    configured = ""
    try:
        configured = public_model_id(settings.stt_model)
    except Exception:
        configured = ""
    models: list[dict[str, object]] = []
    for item in payload.get("models", []):
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("id") or "")
        installed = False
        try:
            size = canonical_size(model_id)
            explicit = settings.stt_model_path if model_id == configured else ""
            installed = model_is_installed(settings.resolved_model_cache_dir(), size, explicit)
        except Exception:
            installed = False
        models.append(
            {
                "id": model_id,
                "provider": item.get("provider"),
                "license": item.get("license"),
                "languages": item.get("languages", []),
                "status": item.get("status"),
                "installed": installed,
                "ready": False,
            }
        )
    return {"models": models, "status": "ok"}
