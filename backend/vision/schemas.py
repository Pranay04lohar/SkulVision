"""
Schemas for the object detection pipeline.

BoundingBox  — axis-aligned box in pixel space
Detection    — single detected object with class, confidence, and bbox
DetectionFrame — full set of detections for one frame pass
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BoundingBox:
    """Axis-aligned bounding box in original frame pixel coordinates."""

    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    @property
    def area(self) -> float:
        return max(0.0, self.width) * max(0.0, self.height)

    def to_xyxy_int(self) -> tuple[int, int, int, int]:
        return (int(self.x1), int(self.y1), int(self.x2), int(self.y2))

    def to_xywh(self) -> tuple[float, float, float, float]:
        return (self.x1, self.y1, self.width, self.height)


@dataclass
class Detection:
    """A single detected object instance."""

    class_id: int
    class_name: str
    confidence: float
    bbox: BoundingBox
    track_id: Optional[int] = None  # populated by a tracker in Phase 2


@dataclass
class DetectionFrame:
    """All detections produced from a single frame inference pass."""

    detections: list[Detection] = field(default_factory=list)
    inference_time_ms: float = 0.0
    frame_width: int = 0
    frame_height: int = 0

    @property
    def count(self) -> int:
        return len(self.detections)

    def filter_by_class(self, class_name: str) -> list[Detection]:
        return [d for d in self.detections if d.class_name == class_name]

    def filter_by_confidence(self, min_conf: float) -> list[Detection]:
        return [d for d in self.detections if d.confidence >= min_conf]
