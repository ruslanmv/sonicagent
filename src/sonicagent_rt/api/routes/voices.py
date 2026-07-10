from fastapi import APIRouter

router = APIRouter(prefix="/voices", tags=["models"])

@router.get("")
async def list_voices() -> dict[str, object]:
    return {"voices": [], "status": "registry scaffold"}
