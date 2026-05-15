"""
Image preprocessing optimized for OCR accuracy.

CLAHE (Contrast Limited Adaptive Histogram Equalization) + mild
sharpening significantly improve OCR on low-contrast signboards
and printed text seen through wearable cameras.
"""

from __future__ import annotations

import cv2
import numpy as np


class OCRPreprocessor:
    """Preprocessing pipeline specifically tuned for text extraction."""

    def enhance_for_ocr(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply CLAHE and sharpening to maximize OCR legibility.

        Accepts BGR (3-channel) or grayscale (1-channel) input.
        Always returns a BGR image (OCR engines typically expect color input).
        """
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame.copy()

        # Adaptive contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Mild unsharp mask for edge sharpness
        kernel = np.array(
            [[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32
        )
        sharpened = cv2.filter2D(enhanced, -1, kernel)

        return cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)

    def crop_text_region(
        self, frame: np.ndarray, bbox_points: list[list[float]]
    ) -> np.ndarray:
        """
        Perspective-correct crop of a potentially rotated text region.

        Uses getPerspectiveTransform to deskew the quad bounding box
        before passing a region to a specialized recognizer.
        """
        pts = np.array(bbox_points, dtype=np.float32)
        w = int(np.linalg.norm(pts[1] - pts[0]))
        h = int(np.linalg.norm(pts[3] - pts[0]))

        if w <= 0 or h <= 0:
            return frame

        dst = np.array(
            [[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32
        )
        M = cv2.getPerspectiveTransform(pts, dst)
        return cv2.warpPerspective(frame, M, (w, h))
