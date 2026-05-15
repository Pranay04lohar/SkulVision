"""
HUD renderer — draws detection boxes, OCR annotations, and status info
directly onto frames using OpenCV primitives.

Design philosophy:
  - Minimal, tactical aesthetic: no decorative elements
  - Every drawn element serves an information purpose
  - Label backgrounds ensure readability on any background color
  - Optional stats panel (off by default — use mobile Menu for connection status)

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
            stats_font_scale=settings.HUD_STATS_FONT_SCALE,
            panel_alpha=settings.HUD_PANEL_ALPHA,
            show_hud_stats=settings.HUD_SHOW_STATS_PANEL,
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

    def _stats_scale_for_frame(self, frame: np.ndarray) -> float:
        """Readable on phone — matched to mobile Menu panel size."""
        ref_w = 640.0
        w = float(frame.shape[1])
        scaled = self._config.stats_font_scale * (w / ref_w)
        return max(0.52, min(0.68, scaled))

    def _draw_menu_style_box(
        self,
        frame: np.ndarray,
        x0: int,
        y0: int,
        box_w: int,
        box_h: int,
    ) -> None:
        """White card + black border — same look as mobile Server IP panel."""
        white = (250, 250, 250)
        black = (17, 17, 17)
        x1, y1 = x0 + box_w, y0 + box_h
        cv2.rectangle(frame, (x0, y0), (x1, y1), white, cv2.FILLED)
        cv2.rectangle(frame, (x0, y0), (x1, y1), black, 2, _LINE)

    def _draw_hud_panel(
        self,
        frame: np.ndarray,
        df: Optional[DetectionFrame],
        ocr: Optional[OCRFrame],
        extra_info: Optional[dict[str, str]],
    ) -> None:
        """
        Stats card on the video — white box / black text like mobile Menu panel.

        Placed top-right so it does not sit under the phone's top-left Menu overlay.
        """
        scale = self._stats_scale_for_frame(frame)
        thickness = 2
        padding = 10
        line_gap = 6
        margin = 10

        black = (17, 17, 17)
        gray = (80, 80, 80)
        accent = (200, 130, 0)  # dark cyan/teal on white (BGR)

        stat_lines: list[tuple[str, tuple[int, int, int]]] = [
            (f"FPS  {self._current_fps:.1f}", accent),
        ]
        if df:
            stat_lines.append(
                (f"DET  {df.count} obj  {df.inference_time_ms:.0f}ms", black)
            )
        if ocr and ocr.count > 0:
            tag = (
                f"(cached ~{ocr.inference_time_ms:.0f}ms)"
                if ocr.cached
                else f"{ocr.inference_time_ms:.0f}ms"
            )
            stat_lines.append((f"OCR  {ocr.count} rgn  {tag}", black))
        elif ocr and ocr.cached:
            stat_lines.append((f"OCR  async ~{ocr.inference_time_ms:.0f}ms", gray))
        if extra_info and "lat" in extra_info:
            stat_lines.append((f"LAT  {extra_info['lat']}", black))

        header_scale = scale * 0.72
        header = "HUD STATS"
        (hw, hh), hbaseline = cv2.getTextSize(header, _FONT, header_scale, 1)

        metrics: list[tuple[str, tuple[int, int, int], int, int, int]] = []
        max_width = hw
        content_height = hh + hbaseline + line_gap
        for text, color in stat_lines:
            (tw, th), baseline = cv2.getTextSize(text, _FONT, scale, thickness)
            metrics.append((text, color, tw, th, baseline))
            max_width = max(max_width, tw)
            content_height += th + baseline + line_gap

        panel_w = min(max_width + padding * 2, int(frame.shape[1] * 0.55))
        panel_h = min(content_height + padding * 2, int(frame.shape[0] * 0.45))

        # Top-left, below the phone Menu pill (~48px)
        x0 = margin
        y0 = margin + 48

        self._draw_menu_style_box(frame, x0, y0, panel_w, panel_h)

        y = y0 + padding
        cv2.putText(
            frame,
            header,
            (x0 + padding, y + hh),
            _FONT,
            header_scale,
            gray,
            1,
            _LINE,
        )
        y += hh + hbaseline + line_gap

        for text, color, _tw, th, baseline in metrics:
            y += th
            cv2.putText(
                frame,
                text,
                (x0 + padding, y),
                _FONT,
                scale,
                color,
                thickness,
                _LINE,
            )
            y += baseline + line_gap

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
