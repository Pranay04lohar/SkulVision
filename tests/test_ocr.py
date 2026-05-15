"""
Unit tests for the OCR pipeline.

No actual OCR model inference is performed here.
Tests validate preprocessing behavior and schema correctness.
"""

from __future__ import annotations

import numpy as np
import pytest

from backend.ocr.preprocessor import OCRPreprocessor
from backend.ocr.schemas import OCRFrame, TextRegion


class TestOCRPreprocessor:
    def setup_method(self) -> None:
        self.preprocessor = OCRPreprocessor()

    def test_enhance_output_shape_bgr(self) -> None:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        enhanced = self.preprocessor.enhance_for_ocr(frame)
        assert enhanced.shape == (480, 640, 3)

    def test_enhance_output_dtype(self) -> None:
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        enhanced = self.preprocessor.enhance_for_ocr(frame)
        assert enhanced.dtype == np.uint8

    def test_enhance_grayscale_input(self) -> None:
        gray = np.zeros((480, 640), dtype=np.uint8)
        enhanced = self.preprocessor.enhance_for_ocr(gray)
        # Output should always be BGR (3-channel)
        assert len(enhanced.shape) == 3
        assert enhanced.shape[2] == 3

    def test_crop_text_region_valid(self) -> None:
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        # Axis-aligned quad representing a 100x50 text region
        bbox_points = [[50.0, 100.0], [150.0, 100.0], [150.0, 150.0], [50.0, 150.0]]
        cropped = self.preprocessor.crop_text_region(frame, bbox_points)
        # Width ~ 100, height ~ 50
        assert cropped.shape[1] == pytest.approx(100, abs=2)
        assert cropped.shape[0] == pytest.approx(50, abs=2)

    def test_crop_degenerate_bbox_returns_frame(self) -> None:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Collapsed zero-area quad
        bbox_points = [[50.0, 50.0], [50.0, 50.0], [50.0, 50.0], [50.0, 50.0]]
        result = self.preprocessor.crop_text_region(frame, bbox_points)
        # Should return original frame unchanged
        assert result.shape == frame.shape


class TestOCRSchemas:
    def test_text_region_top_left(self) -> None:
        region = TextRegion(
            text="Hello",
            confidence=0.95,
            bbox_points=[[10.0, 20.0], [100.0, 20.0], [100.0, 50.0], [10.0, 50.0]],
        )
        assert region.top_left == (10.0, 20.0)

    def test_ocr_frame_texts(self) -> None:
        regions = [
            TextRegion("Hello", 0.9, [[0, 0], [100, 0], [100, 30], [0, 30]]),
            TextRegion("World", 0.85, [[0, 40], [100, 40], [100, 70], [0, 70]]),
        ]
        frame = OCRFrame(regions=regions, inference_time_ms=15.3)
        assert frame.texts == ["Hello", "World"]
        assert frame.count == 2

    def test_ocr_frame_confidence_filter(self) -> None:
        regions = [
            TextRegion("High", 0.95, [[0, 0], [100, 0], [100, 30], [0, 30]]),
            TextRegion("Low", 0.3, [[0, 40], [100, 40], [100, 70], [0, 70]]),
        ]
        frame = OCRFrame(regions=regions)
        filtered = frame.filter_by_confidence(0.5)
        assert len(filtered) == 1
        assert filtered[0].text == "High"
