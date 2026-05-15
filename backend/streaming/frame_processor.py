"""
Per-connection frame processor.

Each WebSocket client gets a dedicated FrameProcessor instance that:
  1. Accepts incoming frame bytes into a bounded async queue
  2. Decodes, resizes, and runs the full pipeline on dequeued frames
  3. Returns rendered JPEG bytes for transmission back to the client

Backpressure:
  The queue has a fixed capacity (FRAME_QUEUE_SIZE). If the queue is full
  when a new frame arrives, the frame is dropped silently. This is the
  correct behavior for a real-time HUD — stale frames are worthless.
  Dropped frames are counted and periodically logged for diagnostics.

This design ensures the event loop is never blocked by inference work
and naturally throttles slower clients without accumulating memory.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from backend.core.config import get_settings
from backend.core.logging_config import get_logger
from backend.overlay.compositor import FrameCompositor
from backend.pipeline.orchestrator import PipelineOrchestrator

logger = get_logger(__name__)


class FrameProcessor:
    """
    Async frame queue and processing bridge for a single WebSocket client.

    Usage:
        processor = FrameProcessor(orchestrator, client_id="abc123")
        await processor.submit_frame(raw_jpeg_bytes)
        result_bytes = await processor.next_result()
    """

    def __init__(
        self, orchestrator: PipelineOrchestrator, client_id: str
    ) -> None:
        self._settings = get_settings()
        self._orchestrator = orchestrator
        self._client_id = client_id
        self._compositor = FrameCompositor()
        self._queue: asyncio.Queue[bytes] = asyncio.Queue(
            maxsize=self._settings.FRAME_QUEUE_SIZE
        )
        self._dropped_frames = 0

    async def submit_frame(self, frame_bytes: bytes) -> None:
        """
        Enqueue a raw JPEG frame for processing.
        Silently drops the frame if the queue is at capacity.
        """
        try:
            self._queue.put_nowait(frame_bytes)
        except asyncio.QueueFull:
            self._dropped_frames += 1
            if self._dropped_frames % 50 == 0:
                logger.debug(
                    "frames_dropped",
                    client_id=self._client_id,
                    total_dropped=self._dropped_frames,
                )

    async def next_result(self) -> Optional[bytes]:
        """
        Dequeue and process one frame.

        Returns rendered JPEG bytes, or None if the queue is empty.
        Returns None if the frame is undecodable.
        """
        if self._queue.empty():
            return None

        raw_bytes = await self._queue.get()
        # Always process the newest frame — skip stale backlog for real-time HUD
        while not self._queue.empty():
            try:
                raw_bytes = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        try:
            frame = self._compositor.decode_frame(raw_bytes)
        except ValueError as exc:
            logger.warning(
                "frame_decode_failed",
                client_id=self._client_id,
                bytes=len(raw_bytes),
                error=str(exc),
            )
            return None

        # Downscale to configured maximum dimension before inference
        frame = self._compositor.resize_max_dimension(
            frame, self._settings.MAX_FRAME_DIMENSION
        )

        context = self._orchestrator.make_context(
            raw_frame=frame,
            client_id=self._client_id,
        )
        context = await self._orchestrator.process_frame(context)

        if context.rendered_frame is None:
            return None

        return self._compositor.encode_jpeg(
            context.rendered_frame,
            quality=self._settings.JPEG_QUALITY,
        )

    @property
    def dropped_frames(self) -> int:
        return self._dropped_frames
