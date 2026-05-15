"""
PipelineOrchestrator — the central coordinator for SkulVision inference.

Hot path per frame (must stay fast):
  Detection → attach cached OCR → HUD render

OCR runs in a background task on a separate thread pool so EasyOCR
never blocks the real-time detection + display loop.
"""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Optional

import numpy as np

from backend.core.config import get_settings
from backend.core.exceptions import PipelineNotInitializedError
from backend.core.logging_config import get_logger
from backend.inference.model_manager import ModelManager, get_model_manager
from backend.ocr.engine import EasyOCREngine
from backend.ocr.schemas import OCRFrame
from backend.overlay.compositor import FrameCompositor
from backend.overlay.renderer import HUDRenderer
from backend.pipeline.context import FrameContext
from backend.vision.detector import YOLODetector

logger = get_logger(__name__)


@dataclass
class _OcrClientState:
    last_run_time: float = 0.0
    in_flight: bool = False
    latest_frame: Optional[np.ndarray] = None


class PipelineOrchestrator:
    """
    Application-scoped pipeline coordinator.

    Detection uses _det_executor; OCR uses _ocr_executor so YOLO and
    EasyOCR can overlap on multi-core CPUs without blocking each other
    on the hot path.
    """

    def __init__(self, model_manager: Optional[ModelManager] = None) -> None:
        self._settings = get_settings()
        self._model_manager = model_manager or get_model_manager()

        self._detector: Optional[YOLODetector] = None
        self._ocr_engine: Optional[EasyOCREngine] = None
        self._renderer = HUDRenderer()
        self._compositor = FrameCompositor()

        self._det_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="skul-det")
        self._ocr_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="skul-ocr")

        self._frame_counter = 0
        self._initialized = False
        self._ocr_cache: dict[str, OCRFrame] = {}
        self._ocr_state: dict[str, _OcrClientState] = {}
        self._ocr_tasks: dict[str, asyncio.Task[None]] = {}

    async def initialize(self) -> None:
        """Load all enabled AI models at application startup."""
        logger.info("pipeline_initializing")
        loop = asyncio.get_event_loop()

        if self._settings.DETECTION_ENABLED:
            self._detector = YOLODetector(self._model_manager)
            await loop.run_in_executor(self._det_executor, self._detector.load)
            logger.info("detection_pipeline_ready")

        if self._settings.OCR_ENABLED:
            self._ocr_engine = EasyOCREngine()
            await loop.run_in_executor(self._ocr_executor, self._ocr_engine.load)
            logger.info("ocr_pipeline_ready", mode="background_async")

        self._initialized = True
        logger.info("pipeline_ready")

    async def process_frame(self, context: FrameContext) -> FrameContext:
        """
        Fast path: detection + cached OCR overlay + render.
        OCR inference is scheduled separately and never awaited here.
        """
        if not self._initialized:
            raise PipelineNotInitializedError(
                "Call orchestrator.initialize() before processing frames."
            )

        loop = asyncio.get_event_loop()
        frame = context.raw_frame
        cache_key = context.client_id or "default"

        if self._detector is not None:
            try:
                context.detection_result = await loop.run_in_executor(
                    self._det_executor, self._detector.detect, frame
                )
            except Exception as exc:
                logger.warning(
                    "detection_stage_failed", error=str(exc), frame_id=context.frame_id
                )

        if self._ocr_engine is not None:
            context.ocr_result = self._get_cached_ocr(cache_key)
            self._schedule_background_ocr(frame, cache_key)

        context.mark_complete()
        extra: dict[str, str] = {}
        if context.total_latency_ms is not None:
            extra["lat"] = f"{context.total_latency_ms:.0f}ms"

        render_result = self._renderer.render(
            frame=frame,
            detection_frame=context.detection_result,
            ocr_frame=context.ocr_result,
            extra_info=extra or None,
        )
        context.rendered_frame = render_result.frame

        self._frame_counter += 1
        if self._frame_counter % 200 == 0:
            logger.info(
                "pipeline_throughput",
                frames_processed=self._frame_counter,
                fps=self._renderer.current_fps,
                latency_ms=context.total_latency_ms,
            )

        return context

    def _get_cached_ocr(self, cache_key: str) -> Optional[OCRFrame]:
        cached = self._ocr_cache.get(cache_key)
        if cached is None:
            return None
        return OCRFrame(
            regions=cached.regions,
            inference_time_ms=cached.inference_time_ms,
            cached=True,
        )

    def _schedule_background_ocr(self, frame: np.ndarray, cache_key: str) -> None:
        """Queue OCR on the latest frame without blocking the hot path."""
        state = self._ocr_state.setdefault(cache_key, _OcrClientState())
        state.latest_frame = frame.copy()

        now = time.time()
        if state.in_flight:
            return
        if now - state.last_run_time < self._settings.OCR_MIN_INTERVAL_SEC:
            return

        existing = self._ocr_tasks.get(cache_key)
        if existing is not None and not existing.done():
            return

        self._ocr_tasks[cache_key] = asyncio.create_task(
            self._run_background_ocr(cache_key),
            name=f"ocr-{cache_key}",
        )

    async def _run_background_ocr(self, cache_key: str) -> None:
        state = self._ocr_state.get(cache_key)
        if state is None or state.latest_frame is None or self._ocr_engine is None:
            return

        state.in_flight = True
        frame = state.latest_frame.copy()
        loop = asyncio.get_event_loop()

        try:
            result = await loop.run_in_executor(
                self._ocr_executor, self._ocr_engine.extract, frame
            )
            self._ocr_cache[cache_key] = result
            state.last_run_time = time.time()
            logger.debug(
                "ocr_background_complete",
                client_id=cache_key,
                regions=result.count,
                ms=result.inference_time_ms,
            )
        except Exception as exc:
            logger.warning("ocr_background_failed", client_id=cache_key, error=str(exc))
        finally:
            state.in_flight = False

    def make_context(
        self,
        raw_frame,
        client_id: Optional[str] = None,
        source_id: str = "default",
    ) -> FrameContext:
        self._frame_counter += 1
        return FrameContext(
            frame_id=self._frame_counter,
            raw_frame=raw_frame,
            client_id=client_id,
            source_id=source_id,
        )

    async def shutdown(self) -> None:
        for task in self._ocr_tasks.values():
            task.cancel()
        self._det_executor.shutdown(wait=False)
        self._ocr_executor.shutdown(wait=False)
        logger.info("pipeline_shutdown")

    @property
    def is_initialized(self) -> bool:
        return self._initialized
