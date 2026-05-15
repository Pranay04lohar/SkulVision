"""
Frame preprocessing for object detection inference.

Implements letterbox resizing — the standard approach for YOLO models:
  1. Scale image to fit target size while preserving aspect ratio
  2. Pad remaining area with gray (114,114,114)
  3. Normalize pixels to [0, 1] float32
  4. Reorder to NCHW channel format

Letterboxing preserves accurate bounding-box coordinate recovery
via the tracked scale and padding values returned alongside the blob.
"""

from __future__ import annotations

import cv2
import numpy as np


class VisionPreprocessor:
    def __init__(self, input_size: tuple[int, int] = (640, 640)) -> None:
        """
        input_size: (width, height) expected by the model.
        """
        self.input_size = input_size

    def preprocess(
        self, frame: np.ndarray
    ) -> tuple[np.ndarray, float, float, int, int]:
        """
        Letterbox-resize and normalize a BGR frame.

        Returns
        -------
        blob      : float32 NCHW tensor ready for ONNX inference
        scale_x   : x scale applied (original_w / letterboxed_w)
        scale_y   : y scale applied (original_h / letterboxed_h)
        pad_x     : horizontal padding in pixels
        pad_y     : vertical padding in pixels
        """
        original_h, original_w = frame.shape[:2]
        target_w, target_h = self.input_size

        scale = min(target_w / original_w, target_h / original_h)
        new_w = int(original_w * scale)
        new_h = int(original_h * scale)

        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        pad_x = (target_w - new_w) // 2
        pad_y = (target_h - new_h) // 2

        padded = np.full((target_h, target_w, 3), 114, dtype=np.uint8)
        padded[pad_y : pad_y + new_h, pad_x : pad_x + new_w] = resized

        # BGR → RGB, HWC → CHW, normalize, add batch dim
        blob = padded[:, :, ::-1].transpose(2, 0, 1).astype(np.float32) / 255.0
        blob = np.ascontiguousarray(blob[np.newaxis])  # (1, 3, H, W)

        # Scale factors map from letterboxed-space back to original-space
        scale_x = original_w / new_w
        scale_y = original_h / new_h

        return blob, scale_x, scale_y, pad_x, pad_y

    def decode_boxes(
        self,
        raw_boxes: np.ndarray,
        scale_x: float,
        scale_y: float,
        pad_x: int,
        pad_y: int,
        original_w: int,
        original_h: int,
    ) -> np.ndarray:
        """
        Map predicted box coordinates from letterboxed-tensor space
        back to original frame pixel space.

        raw_boxes: (N, 4) float array in [x1, y1, x2, y2] format
        """
        boxes = raw_boxes.copy().astype(np.float32)

        # Remove padding offset then apply inverse scale
        boxes[:, 0] = (boxes[:, 0] - pad_x) * scale_x
        boxes[:, 1] = (boxes[:, 1] - pad_y) * scale_y
        boxes[:, 2] = (boxes[:, 2] - pad_x) * scale_x
        boxes[:, 3] = (boxes[:, 3] - pad_y) * scale_y

        # Clamp to frame boundaries
        boxes[:, 0] = np.clip(boxes[:, 0], 0, original_w)
        boxes[:, 1] = np.clip(boxes[:, 1], 0, original_h)
        boxes[:, 2] = np.clip(boxes[:, 2], 0, original_w)
        boxes[:, 3] = np.clip(boxes[:, 3], 0, original_h)

        return boxes
