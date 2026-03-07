"""WebSocket connection manager.

Tracks active WebSocket connections per user and provides
methods for sending data to individual users or broadcasting.
Includes heartbeat support to detect stale connections.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from utils.log import log_info, log_warning, log_debug


class WebSocketManager:
    """Manages active WebSocket connections grouped by user ID."""

    def __init__(self) -> None:
        # user_id → list of active WebSocket connections
        self._connections: dict[str, list[WebSocket]] = {}
        self._lock = asyncio.Lock()

    # ── Connection lifecycle ────────────────────────────────────────────

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        """Accept a WebSocket and register it under a user ID."""
        await websocket.accept()
        async with self._lock:
            self._connections.setdefault(user_id, []).append(websocket)
        log_info(f"[WS] Connected: user={user_id} (total={self.connection_count})")

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket from the active list."""
        async with self._lock:
            conns = self._connections.get(user_id, [])
            if websocket in conns:
                conns.remove(websocket)
            if not conns:
                self._connections.pop(user_id, None)
        log_info(f"[WS] Disconnected: user={user_id} (total={self.connection_count})")

    # ── Send helpers ────────────────────────────────────────────────────

    async def send_to_user(self, user_id: str, data: dict[str, Any]) -> None:
        """Send a JSON message to all connections of a specific user."""
        conns = self._connections.get(user_id, [])
        stale: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(data)
            except (WebSocketDisconnect, RuntimeError):
                stale.append(ws)
        # Clean up stale connections
        for ws in stale:
            await self.disconnect(user_id, ws)

    async def send_text_to_user(self, user_id: str, text: str) -> None:
        """Send a raw text message to all connections of a specific user."""
        conns = self._connections.get(user_id, [])
        stale: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_text(text)
            except (WebSocketDisconnect, RuntimeError):
                stale.append(ws)
        for ws in stale:
            await self.disconnect(user_id, ws)

    async def broadcast(self, data: dict[str, Any]) -> None:
        """Send a JSON message to all connected users."""
        for user_id in list(self._connections.keys()):
            await self.send_to_user(user_id, data)

    # ── Heartbeat ───────────────────────────────────────────────────────

    async def heartbeat(self, websocket: WebSocket, interval: int = 30) -> None:
        """Send periodic ping frames to keep the connection alive.

        Run this as a background task for each connection.
        It will exit when the connection closes.
        """
        try:
            while True:
                await asyncio.sleep(interval)
                try:
                    await websocket.send_json({"type": "ping"})
                except (WebSocketDisconnect, RuntimeError):
                    break
        except asyncio.CancelledError:
            pass

    # ── Introspection ───────────────────────────────────────────────────

    @property
    def connection_count(self) -> int:
        """Total number of active WebSocket connections."""
        return sum(len(conns) for conns in self._connections.values())

    @property
    def connected_users(self) -> list[str]:
        """List of user IDs with active connections."""
        return list(self._connections.keys())


# Module-level singleton
ws_manager = WebSocketManager()
