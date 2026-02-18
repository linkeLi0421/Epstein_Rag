"""WebSocket endpoint for real-time dashboard updates."""

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from dashboard_backend.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])

settings = get_settings()


class ConnectionManager:
    """Manages active WebSocket connections for real-time dashboard updates."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info("WebSocket client connected. Total: %d", len(self.active_connections))

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info("WebSocket client disconnected. Total: %d", len(self.active_connections))

    async def broadcast_json(self, message: dict):
        """Send a JSON message to all connected clients."""
        async with self._lock:
            stale = []
            for connection in self.active_connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    stale.append(connection)
            for conn in stale:
                self.active_connections.remove(conn)


manager = ConnectionManager()


async def broadcast(message: dict):
    """Public helper to broadcast a message from other modules."""
    await manager.broadcast_json(message)


async def _heartbeat(websocket: WebSocket):
    """Send periodic heartbeats to keep the connection alive."""
    try:
        while True:
            await asyncio.sleep(settings.ws_heartbeat_interval)
            await websocket.send_json({
                "type": "heartbeat",
                "data": {"timestamp": datetime.now(timezone.utc).isoformat()},
            })
    except Exception:
        pass  # Connection closed


@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates.

    Clients receive messages with the following types:
    - query_update: New query logged
    - job_update: Job status/progress changed
    - metric_update: New system metrics
    - heartbeat: Periodic keep-alive
    """
    await manager.connect(websocket)
    heartbeat_task = asyncio.create_task(_heartbeat(websocket))

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "data": {
                "message": "Connected to dashboard WebSocket",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        })

        # Listen for client messages (e.g. subscribe/unsubscribe to specific events)
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")

                if msg_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "data": {"timestamp": datetime.now(timezone.utc).isoformat()},
                    })
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Invalid JSON"},
                })
    except WebSocketDisconnect:
        pass
    finally:
        heartbeat_task.cancel()
        await manager.disconnect(websocket)
