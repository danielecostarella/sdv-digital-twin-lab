"""WebSocket connection manager — fan-out broadcast to all connected browsers."""

import json
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._active: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._active.add(ws)
        logger.debug("Client connected (%d total)", len(self._active))

    def disconnect(self, ws: WebSocket) -> None:
        self._active.discard(ws)
        logger.debug("Client disconnected (%d remaining)", len(self._active))

    async def broadcast(self, data: dict) -> None:
        if not self._active:
            return
        message = json.dumps(data)
        dead: set[WebSocket] = set()
        for ws in self._active:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        self._active -= dead


manager = ConnectionManager()
