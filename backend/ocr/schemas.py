"""
Schemas for the OCR pipeline.

TextRegion   — a single detected text block with quad bounding box
OCRFrame     — all text regions found in one frame
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TextRegion:
    """
    A detected text block.

    bbox_points: four corners [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
    in clockwise order starting from the top-left corner.
    Using a quad (not AABB) supports rotated/perspective text.
    """

    text: str
    confidence: float
    bbox_points: list[list[float]]

    @property
    def top_left(self) -> tuple[float, float]:
        return (self.bbox_points[0][0], self.bbox_points[0][1])

    @property
    def top_right(self) -> tuple[float, float]:
        return (self.bbox_points[1][0], self.bbox_points[1][1])

    @property
    def approx_width(self) -> float:
        dx = self.bbox_points[1][0] - self.bbox_points[0][0]
        dy = self.bbox_points[1][1] - self.bbox_points[0][1]
        return (dx**2 + dy**2) ** 0.5

    @property
    def approx_height(self) -> float:
        dx = self.bbox_points[3][0] - self.bbox_points[0][0]
        dy = self.bbox_points[3][1] - self.bbox_points[0][1]
        return (dx**2 + dy**2) ** 0.5


@dataclass
class OCRFrame:
    """All text regions extracted from a single frame."""

    regions: list[TextRegion] = field(default_factory=list)
    inference_time_ms: float = 0.0
    cached: bool = False  # True when served from async cache, not this frame's run

    @property
    def texts(self) -> list[str]:
        return [r.text for r in self.regions]

    @property
    def count(self) -> int:
        return len(self.regions)

    def filter_by_confidence(self, min_conf: float) -> list[TextRegion]:
        return [r for r in self.regions if r.confidence >= min_conf]
