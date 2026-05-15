"""
WebSocket connection handler.

Protocol:
  - Client connects to /ws/stream
  - Client sends raw JPEG bytes continuously (camera frames)
  - Server replies with rendered JPEG bytes (HUD-overlaid frames)
  - Text JSON messages can be used for control (ping/pong, config)

Connection lifecycle:
  accept → spawn receive + send coroutines → await first failure/disconnect → cleanup

Receive loop and send loop run concurrently via asyncio.gather.
If either exits (disconnect, error), both are cancelled cleanly.

The send loop paces output at TARGET_FPS using a sleep interval.
This prevents flooding slow clients while keeping the pipeline running.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from backend.core.config import get_settings
from backend.core.logging_config import get_logger
from backend.pipeline.orchestrator import PipelineOrchestrator
from backend.streaming.frame_processor import FrameProcessor

logger = get_logger(__name__)


class WebSocketHandler:
    """
    Manages the full lifecycle of a single WebSocket client session.

    One instance is shared across all connections (stateless).
    Per-connection state lives inside the FrameProcessor.
    """

    def __init__(self, orchestrator: PipelineOrchestrator) -> None:
        self._orchestrator = orchestrator
        self._settings = get_settings()

    async def handle(self, websocket: WebSocket) -> None:
        """Entry point for a new WebSocket connection."""
        client_id = str(uuid.uuid4())[:8]
        await websocket.accept()
        logger.info("client_connected", client_id=client_id, remote=websocket.client)

        processor = FrameProcessor(self._orchestrator, client_id=client_id)

        try:
            await self._run_duplex(websocket, processor, client_id)
        except WebSocketDisconnect:
            logger.info("client_disconnected", client_id=client_id)
        except Exception as exc:
            logger.error("websocket_error", client_id=client_id, error=str(exc))
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.close(code=1011)
        finally:
            logger.info(
                "client_session_ended",
                client_id=client_id,
                dropped_frames=processor.dropped_frames,
            )

    async def _run_duplex(
        self,
        websocket: WebSocket,
        processor: FrameProcessor,
        client_id: str,
    ) -> None:
        """Run receive and send loops concurrently; cancel both on first exit."""
        receive_task = asyncio.create_task(
            self._receive_loop(websocket, processor, client_id),
            name=f"recv-{client_id}",
        )
        send_task = asyncio.create_task(
            self._send_loop(websocket, processor, client_id),
            name=f"send-{client_id}",
        )

        done, pending = await asyncio.wait(
            [receive_task, send_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Re-raise any exception from completed tasks
        for task in done:
            exc = task.exception()
            if exc is not None:
                raise exc

    async def _receive_loop(
        self,
        websocket: WebSocket,
        processor: FrameProcessor,
        client_id: str,
    ) -> None:
        """Continuously receive bytes from the client and enqueue them."""
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            data = message.get("bytes")
            if not data:
                continue
            if len(data) < 100:
                logger.debug(
                    "frame_too_small",
                    client_id=client_id,
                    bytes=len(data),
                )
                continue
            await processor.submit_frame(data)

    async def _send_loop(
        self,
        websocket: WebSocket,
        processor: FrameProcessor,
        client_id: str,
    ) -> None:
        """Send rendered frames as fast as the pipeline produces them (up to TARGET_FPS)."""
        min_interval = 1.0 / self._settings.TARGET_FPS
        last_sent = 0.0

        while True:
            result = await processor.next_result()
            if result is None:
                await asyncio.sleep(0.01)
                continue

            loop = asyncio.get_running_loop()
            elapsed = loop.time() - last_sent
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)

            await websocket.send_bytes(result)
            last_sent = loop.time()
