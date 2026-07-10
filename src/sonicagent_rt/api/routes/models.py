from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/models", tags=["models"])

@router.get("/stt")
async def list_stt_models() -> dict[str, object]:
    return {"models": [], "status": "registry scaffold"}

@router.post("/prefetch", status_code=501)
async def prefetch() -> None:
    raise HTTPException(501, "Model prefetch is not implemented in the scaffold")
