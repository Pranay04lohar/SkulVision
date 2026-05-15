"""
Schemas and constants for the HUD overlay system.

Color palette uses BGR ordering (OpenCV convention).
PALETTE provides named semantic colors so downstream renderers
remain consistent and the palette can be swapped with a single edit.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Color:
    """BGR color triple (OpenCV convention)."""

    b: int
    g: int
    r: int

    def as_tuple(self) -> tuple[int, int, int]:
        return (self.b, self.g, self.r)

    def as_rgb(self) -> tuple[int, int, int]:
        return (self.r, self.g, self.b)


# Tactical HUD color palette — minimal, high-contrast, readable on any background
PALETTE: dict[str, Color] = {
    "detection_box":    Color(b=0,   g=255, r=0),    # green
    "detection_label":  Color(b=255, g=255, r=255),  # white
    "ocr_box":          Color(b=0,   g=165, r=255),  # orange
    "ocr_text":         Color(b=0,   g=255, r=255),  # yellow
    "hud_primary":      Color(b=255, g=255, r=0),    # cyan
    "hud_secondary":    Color(b=180, g=180, r=180),  # light gray
    "warning":          Color(b=0,   g=0,   r=255),  # red
    "label_bg":         Color(b=0,   g=0,   r=0),    # black
}


@dataclass
class OverlayConfig:
    """Runtime configuration for the HUD renderer."""

    show_detection_boxes: bool = True
    show_detection_labels: bool = True
    show_detection_confidence: bool = True
    show_ocr_boxes: bool = True
    show_ocr_text: bool = True
    show_hud_stats: bool = False
    font_scale: float = 0.6
    thickness: int = 2
    alpha: float = 0.7
    stats_font_scale: float = 0.72
    stats_thickness: int = 2
    panel_alpha: float = 0.75


@dataclass
class RenderResult:
    """Output of a single HUD render pass."""

    frame: np.ndarray
    render_time_ms: float
