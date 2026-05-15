"""
Unit tests for the vision pipeline.

These tests are purely logic-level and do not require a GPU, ONNX model,
or camera. They validate schemas, preprocessor math, and coordinate recovery.
"""

from __future__ import annotations

import numpy as np
import pytest

from backend.vision.schemas import BoundingBox, Detection, DetectionFrame
from backend.vision.preprocessor import VisionPreprocessor


class TestBoundingBox:
    def test_dimensions(self) -> None:
        bbox = BoundingBox(x1=10, y1=20, x2=110, y2=120)
        assert bbox.width == 100
        assert bbox.height == 100

    def test_center(self) -> None:
        bbox = BoundingBox(x1=0, y1=0, x2=100, y2=80)
        assert bbox.center == (50.0, 40.0)

    def test_area(self) -> None:
        bbox = BoundingBox(x1=10, y1=10, x2=60, y2=60)
        assert bbox.area == 2500.0

    def test_to_xyxy_int(self) -> None:
        bbox = BoundingBox(x1=10.7, y1=20.2, x2=110.9, y2=120.1)
        assert bbox.to_xyxy_int() == (10, 20, 110, 120)

    def test_to_xywh(self) -> None:
        bbox = BoundingBox(x1=10, y1=20, x2=110, y2=120)
        x, y, w, h = bbox.to_xywh()
        assert x == 10 and y == 20 and w == 100 and h == 100


class TestVisionPreprocessor:
    def setup_method(self) -> None:
        self.preprocessor = VisionPreprocessor(input_size=(640, 640))

    def test_output_tensor_shape(self) -> None:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        blob, *_ = self.preprocessor.preprocess(frame)
        assert blob.shape == (1, 3, 640, 640)

    def test_output_dtype_and_range(self) -> None:
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 200
        blob, *_ = self.preprocessor.preprocess(frame)
        assert blob.dtype == np.float32
        assert blob.min() >= 0.0
        assert blob.max() <= 1.0

    def test_square_input_no_padding(self) -> None:
        frame = np.zeros((640, 640, 3), dtype=np.uint8)
        blob, scale_x, scale_y, pad_x, pad_y = self.preprocessor.preprocess(frame)
        assert pad_x == 0 and pad_y == 0
        assert scale_x == pytest.approx(1.0, abs=0.01)
        assert scale_y == pytest.approx(1.0, abs=0.01)

    def test_decode_boxes_roundtrip(self) -> None:
        """Boxes encoded through letterbox then decoded should be close to original."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        _, scale_x, scale_y, pad_x, pad_y = self.preprocessor.preprocess(frame)

        # Simulate a box in original frame space, forward-transform to tensor space
        orig_box = np.array([[100, 80, 300, 200]], dtype=np.float32)
        # Reverse: encode to tensor space first
        tensor_box = orig_box.copy()
        tensor_box[:, 0] = orig_box[:, 0] / scale_x + pad_x
        tensor_box[:, 1] = orig_box[:, 1] / scale_y + pad_y
        tensor_box[:, 2] = orig_box[:, 2] / scale_x + pad_x
        tensor_box[:, 3] = orig_box[:, 3] / scale_y + pad_y

        recovered = self.preprocessor.decode_boxes(
            tensor_box, scale_x, scale_y, pad_x, pad_y, 640, 480
        )

        np.testing.assert_allclose(recovered, orig_box, atol=2.0)


class TestDetectionFrame:
    def test_count(self) -> None:
        dets = [
            Detection(0, "person", 0.9, BoundingBox(0, 0, 100, 200)),
            Detection(2, "car", 0.8, BoundingBox(200, 100, 500, 300)),
        ]
        frame = DetectionFrame(detections=dets, frame_width=640, frame_height=480)
        assert frame.count == 2

    def test_filter_by_class(self) -> None:
        dets = [
            Detection(0, "person", 0.9, BoundingBox(0, 0, 100, 200)),
            Detection(2, "car", 0.8, BoundingBox(200, 100, 500, 300)),
            Detection(0, "person", 0.7, BoundingBox(300, 50, 400, 250)),
        ]
        frame = DetectionFrame(detections=dets)
        persons = frame.filter_by_class("person")
        assert len(persons) == 2

    def test_filter_by_confidence(self) -> None:
        dets = [
            Detection(0, "person", 0.9, BoundingBox(0, 0, 100, 200)),
            Detection(2, "car", 0.4, BoundingBox(200, 100, 500, 300)),
        ]
        frame = DetectionFrame(detections=dets)
        high_conf = frame.filter_by_confidence(0.5)
        assert len(high_conf) == 1
        assert high_conf[0].class_name == "person"
