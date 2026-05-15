"""
Unit tests for the pipeline layer.

Tests FrameContext lifecycle and FrameCompositor encode/decode roundtrips.
Does not require models to be loaded.
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from backend.pipeline.context import FrameContext
from backend.overlay.compositor import FrameCompositor


class TestFrameContext:
    def _make_context(self) -> FrameContext:
        return FrameContext(
            frame_id=1,
            raw_frame=np.zeros((480, 640, 3), dtype=np.uint8),
            client_id="test-client",
        )

    def test_initial_state(self) -> None:
        ctx = self._make_context()
        assert ctx.frame_id == 1
        assert ctx.detection_result is None
        assert ctx.ocr_result is None
        assert ctx.rendered_frame is None
        assert ctx.total_latency_ms is None

    def test_mark_complete(self) -> None:
        ctx = self._make_context()
        time.sleep(0.005)  # small sleep to ensure measurable latency
        ctx.mark_complete()
        assert ctx.total_latency_ms is not None
        assert ctx.total_latency_ms >= 0.0

    def test_has_detections_false_when_none(self) -> None:
        ctx = self._make_context()
        assert not ctx.has_detections()

    def test_has_text_false_when_none(self) -> None:
        ctx = self._make_context()
        assert not ctx.has_text()


class TestFrameCompositor:
    def test_encode_decode_roundtrip(self) -> None:
        original = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        encoded = FrameCompositor.encode_jpeg(original, quality=95)
        assert isinstance(encoded, bytes)
        assert len(encoded) > 0

        decoded = FrameCompositor.decode_frame(encoded)
        assert decoded.shape == original.shape
        assert decoded.dtype == np.uint8

    def test_encode_produces_smaller_file_at_lower_quality(self) -> None:
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        high_q = FrameCompositor.encode_jpeg(frame, quality=95)
        low_q = FrameCompositor.encode_jpeg(frame, quality=30)
        assert len(low_q) < len(high_q)

    def test_decode_invalid_bytes_raises(self) -> None:
        with pytest.raises(ValueError):
            FrameCompositor.decode_frame(b"not a valid image")

    def test_resize_within_bounds_no_op(self) -> None:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = FrameCompositor.resize_max_dimension(frame, 1280)
        assert result.shape == frame.shape

    def test_resize_downscales_large_frame(self) -> None:
        frame = np.zeros((2160, 3840, 3), dtype=np.uint8)  # 4K
        result = FrameCompositor.resize_max_dimension(frame, 1280)
        assert max(result.shape[:2]) == 1280

    def test_resize_preserves_aspect_ratio(self) -> None:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)  # 4:3 aspect
        result = FrameCompositor.resize_max_dimension(frame, 320)
        h, w = result.shape[:2]
        assert abs(w / h - 640 / 480) < 0.01
