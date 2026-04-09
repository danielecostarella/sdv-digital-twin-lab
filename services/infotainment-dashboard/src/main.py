"""Infotainment Dashboard — FastAPI application."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .broker_client import subscribe_loop
from .state import vehicle_state
from .websocket_bridge import manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [dashboard] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    async def on_update(payload: dict) -> None:
        vehicle_state.update(payload)
        await manager.broadcast(vehicle_state.copy())

    task = asyncio.create_task(subscribe_loop(on_update))
    logger.info("KUKSA subscriber task started")
    try:
        yield
    finally:
        task.cancel()
        logger.info("KUKSA subscriber task stopped")


app = FastAPI(
    title="SDV Digital Twin Lab — Infotainment Dashboard",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/state")
async def get_state():
    return vehicle_state.copy()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send the current state immediately on connect
        await websocket.send_json(vehicle_state.copy())
        while True:
            # Keep the connection alive; browser sends periodic pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Serve static files last so API routes take priority
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
