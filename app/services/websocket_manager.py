import asyncio
import json
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import WebSocket

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time dashboard updates."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.append(websocket)
        logger.info("websocket_connected", total=len(self._connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self._connections:
                self._connections.remove(websocket)
        logger.info("websocket_disconnected", total=len(self._connections))

    async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        """Send an event to all connected clients."""
        message = json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(UTC).isoformat(),
        }, default=str)

        async with self._lock:
            dead = []
            for ws in self._connections:
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._connections.remove(ws)

    async def broadcast_collection_started(self, competitor_id: int, competitor_name: str) -> None:
        await self.broadcast("collection_started", {
            "competitor_id": competitor_id,
            "competitor_name": competitor_name,
        })

    async def broadcast_collection_completed(
        self, competitor_id: int, competitor_name: str,
        records_collected: int, elapsed: float, changes: int,
    ) -> None:
        await self.broadcast("collection_completed", {
            "competitor_id": competitor_id,
            "competitor_name": competitor_name,
            "records_collected": records_collected,
            "elapsed_seconds": elapsed,
            "changes_detected": changes,
        })

    async def broadcast_collection_failed(
        self, competitor_id: int, competitor_name: str, error: str,
    ) -> None:
        await self.broadcast("collection_failed", {
            "competitor_id": competitor_id,
            "competitor_name": competitor_name,
            "error": error,
        })

    async def broadcast_changes_detected(
        self, competitor_id: int, changes: list[dict[str, Any]],
    ) -> None:
        await self.broadcast("changes_detected", {
            "competitor_id": competitor_id,
            "changes": changes,
        })

    @property
    def connection_count(self) -> int:
        return len(self._connections)


ws_manager = ConnectionManager()
