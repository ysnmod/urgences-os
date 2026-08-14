from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket import manager
from app.utils.db_utils import get_db
from app.dependencies import get_current_user
from app.models import Personnel

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Wait for messages from client (ping)
            data = await websocket.receive_text()
            # Keep connection alive
            await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
