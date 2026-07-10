import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

@router.websocket("/realtime/{session_id}")
async def realtime(websocket: WebSocket, session_id: str) -> None:
    # TODO: validate a short-lived session token and origin before accept.
    await websocket.accept()
    await websocket.send_json({"type": "session.created", "session_id": session_id, "status": "scaffold"})
    try:
        while True:
            message = await websocket.receive()
            if message.get("text"):
                event = json.loads(message["text"])
                if event.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif event.get("type") == "response.cancel":
                    await websocket.send_json({"type": "response.cancelled", "reason": "scaffold"})
                else:
                    await websocket.send_json({"type": "warning", "message": "Control event accepted by scaffold only"})
            elif message.get("bytes") is not None:
                await websocket.send_json({"type": "warning", "message": "Binary audio received; inference pipeline is not implemented"})
    except WebSocketDisconnect:
        return
