"""
HUD renderer — draws detection boxes, OCR annotations, and status info
directly onto frames using OpenCV primitives.

Design philosophy:
  - Minimal, tactical aesthetic: no decorative elements
  - Every drawn element serves an information purpose
  - Label backgrounds ensure readability on any background color
  - FPS counter and inference times are always visible in top-left

Rendering pipeline per frame:
  1. Copy input frame (never mutate in-place)
  2. Draw detection bounding boxes + labels
  3. Draw OCR quad boxes + text
  4. Draw HUD status panel (top-left corner)
"""

from __future__ import annotations

import time
from typing import Optional

import cv2
import numpy as np

from backend.core.config import get_settings
from backend.ocr.schemas import OCRFrame
from backend.overlay.schemas import PALETTE, OverlayConfig, RenderResult
from backend.vision.schemas import DetectionFrame

_FONT = cv2.FONT_HERSHEY_SIMPLEX
_LINE = cv2.LINE_AA


class HUDRenderer:
    """
    Stateful HUD renderer.

    Maintains an FPS counter across frames so the status panel
    always shows real throughput rather than per-frame estimates.
    """

    def __init__(self, config: Optional[OverlayConfig] = None) -> None:
        settings = get_settings()
        self._config = config or OverlayConfig(
            font_scale=settings.OVERLAY_FONT_SCALE,
            thickness=settings.OVERLAY_THICKNESS,
            alpha=settings.OVERLAY_ALPHA,
        )
        self._frame_count = 0
        self._fps_window_start = time.time()
        self._current_fps = 0.0

    def render(
        self,
        frame: np.ndarray,
        detection_frame: Optional[DetectionFrame] = None,
        ocr_frame: Optional[OCRFrame] = None,
        extra_info: Optional[dict[str, str]] = None,
    ) -> RenderResult:
        """
        Composite all HUD layers onto a copy of the input frame.

        Parameters
        ----------
        frame           : BGR source frame
        detection_frame : object detection results (optional)
        ocr_frame       : OCR results (optional)
        extra_info      : arbitrary key-value strings for the HUD panel
        """
        t0 = time.perf_counter()
        output = frame.copy()

        if detection_frame and self._config.show_detection_boxes:
            self._draw_detections(output, detection_frame)

        if ocr_frame and self._config.show_ocr_boxes:
            self._draw_ocr(output, ocr_frame)

        if self._config.show_hud_stats:
            self._draw_hud_panel(output, detection_frame, ocr_frame, extra_info)

        self._tick_fps()
        render_ms = (time.perf_counter() - t0) * 1000.0
        return RenderResult(frame=output, render_time_ms=render_ms)

    # ------------------------------------------------------------------
    # Drawing primitives
    # ------------------------------------------------------------------

    def _draw_detections(
        self, frame: np.ndarray, df: DetectionFrame
    ) -> None:
        cfg = self._config
        box_color = PALETTE["detection_box"].as_tuple()
        label_color = PALETTE["detection_label"].as_tuple()
        bg_color = PALETTE["label_bg"].as_tuple()

        for det in df.detections:
            x1, y1, x2, y2 = det.bbox.to_xyxy_int()
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, cfg.thickness)

            if cfg.show_detection_labels:
                label = det.class_name
                if cfg.show_detection_confidence:
                    label = f"{label} {det.confidence:.2f}"

                (tw, th), baseline = cv2.getTextSize(
                    label, _FONT, cfg.font_scale, cfg.thickness
                )
                label_y = max(y1 - 6, th + 4)

                # Semi-opaque label backing rectangle
                cv2.rectangle(
                    frame,
                    (x1, label_y - th - baseline - 2),
                    (x1 + tw + 6, label_y + 2),
                    bg_color,
                    cv2.FILLED,
                )
                cv2.putText(
                    frame, label, (x1 + 3, label_y),
                    _FONT, cfg.font_scale, label_color, cfg.thickness, _LINE,
                )

    def _draw_ocr(self, frame: np.ndarray, ocr: OCRFrame) -> None:
        cfg = self._config
        box_color = PALETTE["ocr_box"].as_tuple()
        text_color = PALETTE["ocr_text"].as_tuple()

        for region in ocr.regions:
            pts = np.array(region.bbox_points, dtype=np.int32)
            cv2.polylines(
                frame, [pts], isClosed=True, color=box_color, thickness=cfg.thickness
            )

            if cfg.show_ocr_text and region.text:
                x = int(region.top_left[0])
                y = max(int(region.top_left[1]) - 6, 14)
                cv2.putText(
                    frame, region.text, (x, y),
                    _FONT, cfg.font_scale * 0.85, text_color, 1, _LINE,
                )

    def _draw_hud_panel(
        self,
        frame: np.ndarray,
        df: Optional[DetectionFrame],
        ocr: Optional[OCRFrame],
        extra_info: Optional[dict[str, str]],
    ) -> None:
        primary = PALETTE["hud_primary"].as_tuple()
        secondary = PALETTE["hud_secondary"].as_tuple()
        line_height = 18
        x, y = 8, 20

        lines: list[tuple[str, tuple[int, int, int]]] = [
            (f"FPS  {self._current_fps:.1f}", primary),
        ]

        if df:
            lines.append((f"DET  {df.count} obj  {df.inference_time_ms:.0f}ms", secondary))
        if ocr:
            lines.append((f"OCR  {ocr.count} rgn  {ocr.inference_time_ms:.0f}ms", secondary))
        if extra_info:
            for k, v in extra_info.items():
                lines.append((f"{k}: {v}", secondary))

        for i, (text, color) in enumerate(lines):
            cv2.putText(
                frame, text, (x, y + i * line_height),
                _FONT, 0.45, color, 1, _LINE,
            )

    # ------------------------------------------------------------------
    # FPS tracking
    # ------------------------------------------------------------------

    def _tick_fps(self) -> None:
        self._frame_count += 1
        now = time.time()
        elapsed = now - self._fps_window_start
        if elapsed >= 1.0:
            self._current_fps = self._frame_count / elapsed
            self._frame_count = 0
            self._fps_window_start = now

    @property
    def current_fps(self) -> float:
        return self._current_fps
