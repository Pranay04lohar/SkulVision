"""
Central API router.

Aggregates all sub-routers and registers the WebSocket endpoint.
The ws_handler is injected at startup via configure() so the router
module itself has no import-time side effects.
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket

from backend.api.health import router as health_router
from backend.api.ws_handler import WebSocketHandler

router = APIRouter()
router.include_router(health_router)

_ws_handler: WebSocketHandler | None = None


def configure(ws_handler: WebSocketHandler) -> None:
    """Inject the WebSocket handler instance after startup initialization."""
    global _ws_handler
    _ws_handler = ws_handler


@router.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket) -> None:
    """
    Primary streaming endpoint.

    Binary frames in → HUD-rendered frames out.
    Closes with code 1011 (Internal Error) if the pipeline is not ready.
    """
    if _ws_handler is None:
        await websocket.close(code=1011, reason="Pipeline not initialized")
        return
    await _ws_handler.handle(websocket)
