"""
FrameContext — the unit of work for the SkulVision pipeline.

Every frame entering the system is wrapped in a FrameContext.
The context accumulates results as it moves through each stage
(detection → OCR → overlay), providing a single coherent object
for logging, debugging, and downstream consumers.

This design avoids passing many positional arguments between stages
and makes it trivial to add new stages without breaking existing ones.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from backend.ocr.schemas import OCRFrame
from backend.vision.schemas import DetectionFrame


@dataclass
class FrameContext:
    """
    Carries all data produced for a single camera frame through the pipeline.

    Lifecycle:
      1. Created by PipelineOrchestrator.make_context()
      2. Passed through each active pipeline stage
      3. mark_complete() called after HUD rendering
      4. Encoded output sent back to client
    """

    frame_id: int
    raw_frame: np.ndarray
    timestamp: float = field(default_factory=time.time)

    # Populated by inference stages
    detection_result: Optional[DetectionFrame] = None
    ocr_result: Optional[OCRFrame] = None

    # Populated by the overlay renderer
    rendered_frame: Optional[np.ndarray] = None

    # Timing
    pipeline_start_ms: float = field(
        default_factory=lambda: time.perf_counter() * 1000.0
    )
    pipeline_end_ms: Optional[float] = None

    # Routing metadata
    source_id: str = "default"
    client_id: Optional[str] = None

    @property
    def total_latency_ms(self) -> Optional[float]:
        """Wall-clock pipeline latency from context creation to completion."""
        if self.pipeline_end_ms is None:
            return None
        return self.pipeline_end_ms - self.pipeline_start_ms

    def mark_complete(self) -> None:
        """Stamp the pipeline completion time."""
        self.pipeline_end_ms = time.perf_counter() * 1000.0

    def has_detections(self) -> bool:
        return self.detection_result is not None and self.detection_result.count > 0

    def has_text(self) -> bool:
        return self.ocr_result is not None and self.ocr_result.count > 0
