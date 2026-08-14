from fastapi import WebSocket
from typing import List
import json


class ConnectionManager:
    """Manage WebSocket connections for real-time updates"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        """Broadcast to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                # Remove disconnected clients
                self.active_connections.remove(connection)

    async def broadcast_event(
        self, event_type: str, sejour_id: int = None, data: dict = None
    ):
        """Broadcast a patient event to all clients"""
        message = {
            "type": event_type,
            "sejour_id": sejour_id,
            "data": data or {},
        }
        await self.broadcast(message)


# Global manager instance
manager = ConnectionManager()
