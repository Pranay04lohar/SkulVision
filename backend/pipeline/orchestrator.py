"""
PipelineOrchestrator — the central coordinator for SkulVision inference.

Execution order per frame:
  FrameContext
    → [Stage 1] Object Detection   (YOLODetector, if DETECTION_ENABLED)
    → [Stage 2] OCR Extraction     (EasyOCREngine, if OCR_ENABLED)
    → [Stage 3] HUD Overlay Render (HUDRenderer, always)
    → Encoded JPEG output

Stage isolation:
  - Each stage failure is caught and logged individually.
  - A failing stage produces a None result; downstream stages degrade
    gracefully rather than crashing the connection.

Async execution:
  - Inference stages are CPU-bound and use run_in_executor so they
    don't block the FastAPI event loop.
  - A single-threaded executor is used so ONNX sessions, which are not
    guaranteed thread-safe on the same instance, are serialized.

Scaling hook:
  - Replace run_in_executor with a Ray actor pool or a process pool
    for true multicore inference scaling (Phase 3).
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from backend.core.config import get_settings
from backend.core.exceptions import PipelineNotInitializedError
from backend.core.logging_config import get_logger
from backend.inference.model_manager import ModelManager, get_model_manager
from backend.ocr.engine import EasyOCREngine
from backend.overlay.compositor import FrameCompositor
from backend.overlay.renderer import HUDRenderer
from backend.pipeline.context import FrameContext
from backend.vision.detector import YOLODetector

logger = get_logger(__name__)


class PipelineOrchestrator:
    """
    Application-scoped pipeline coordinator.

    One orchestrator instance is shared across all WebSocket connections.
    Thread-safety is ensured via the ThreadPoolExecutor which serializes
    CPU-bound inference calls.
    """

    def __init__(self, model_manager: Optional[ModelManager] = None) -> None:
        self._settings = get_settings()
        self._model_manager = model_manager or get_model_manager()

        self._detector: Optional[YOLODetector] = None
        self._ocr_engine: Optional[EasyOCREngine] = None
        self._renderer = HUDRenderer()
        self._compositor = FrameCompositor()

        # Single-threaded executor keeps ONNX session calls serialized
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="skul-infer")

        self._frame_counter = 0
        self._initialized = False

    async def initialize(self) -> None:
        """
        Load all enabled AI models.
        Called once during application startup (lifespan context).
        """
        logger.info("pipeline_initializing")
        loop = asyncio.get_event_loop()

        if self._settings.DETECTION_ENABLED:
            self._detector = YOLODetector(self._model_manager)
            await loop.run_in_executor(self._executor, self._detector.load)
            logger.info("detection_pipeline_ready")

        if self._settings.OCR_ENABLED:
            self._ocr_engine = EasyOCREngine()
            await loop.run_in_executor(self._executor, self._ocr_engine.load)
            logger.info("ocr_pipeline_ready")

        self._initialized = True
        logger.info("pipeline_ready")

    async def process_frame(self, context: FrameContext) -> FrameContext:
        """
        Execute the full inference pipeline for one frame context.

        Each stage populates the corresponding field on the context.
        Stage failures degrade gracefully (logged, result stays None).
        """
        if not self._initialized:
            raise PipelineNotInitializedError(
                "Call orchestrator.initialize() before processing frames."
            )

        loop = asyncio.get_event_loop()
        frame = context.raw_frame

        # --- Stage 1: Object Detection ---
        if self._detector is not None:
            try:
                context.detection_result = await loop.run_in_executor(
                    self._executor, self._detector.detect, frame
                )
            except Exception as exc:
                logger.warning("detection_stage_failed", error=str(exc), frame_id=context.frame_id)

        # --- Stage 2: OCR ---
        if self._ocr_engine is not None:
            try:
                context.ocr_result = await loop.run_in_executor(
                    self._executor, self._ocr_engine.extract, frame
                )
            except Exception as exc:
                logger.warning("ocr_stage_failed", error=str(exc), frame_id=context.frame_id)

        # --- Stage 3: HUD Rendering ---
        extra: dict[str, str] = {}
        if context.detection_result:
            extra["lat"] = f"{context.detection_result.inference_time_ms:.0f}ms"

        render_result = self._renderer.render(
            frame=frame,
            detection_frame=context.detection_result,
            ocr_frame=context.ocr_result,
            extra_info=extra or None,
        )
        context.rendered_frame = render_result.frame
        context.mark_complete()

        # Periodic throughput logging
        self._frame_counter += 1
        if self._frame_counter % 200 == 0:
            logger.info(
                "pipeline_throughput",
                frames_processed=self._frame_counter,
                fps=self._renderer.current_fps,
                latency_ms=context.total_latency_ms,
            )

        return context

    def make_context(
        self,
        raw_frame,
        client_id: Optional[str] = None,
        source_id: str = "default",
    ) -> FrameContext:
        """Factory method — creates a new FrameContext with a unique frame ID."""
        self._frame_counter += 1
        return FrameContext(
            frame_id=self._frame_counter,
            raw_frame=raw_frame,
            client_id=client_id,
            source_id=source_id,
        )

    async def shutdown(self) -> None:
        """Graceful shutdown — flush executor."""
        self._executor.shutdown(wait=True)
        logger.info("pipeline_shutdown")

    @property
    def is_initialized(self) -> bool:
        return self._initialized
