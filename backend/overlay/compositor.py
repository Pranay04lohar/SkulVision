"""
Frame compositor — encode/decode, resize, and alpha blend utilities.

Kept as pure static methods so it can be used anywhere in the pipeline
without instantiation or state concerns.
"""

from __future__ import annotations

import cv2
import numpy as np


class FrameCompositor:
    """
    Utility class for frame-level operations.

    All methods are static — no instance state required.
    """

    @staticmethod
    def encode_jpeg(frame: np.ndarray, quality: int = 85) -> bytes:
        """Encode a BGR numpy frame to JPEG bytes for WebSocket transmission."""
        success, buffer = cv2.imencode(
            ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality]
        )
        if not success:
            raise ValueError("JPEG encoding failed")
        return buffer.tobytes()

    @staticmethod
    def decode_frame(data: bytes) -> np.ndarray:
        """
        Decode JPEG (or PNG) bytes to a BGR numpy array.

        Raises ValueError if decoding fails (e.g. corrupt data).
        """
        arr = np.frombuffer(data, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError(
                "Frame decode returned None — data may be corrupt or not a valid image."
            )
        return frame

    @staticmethod
    def resize_max_dimension(frame: np.ndarray, max_dim: int) -> np.ndarray:
        """
        Downscale a frame so its longest side equals max_dim.
        Aspect ratio is preserved. No-ops if already within bounds.
        """
        h, w = frame.shape[:2]
        if max(h, w) <= max_dim:
            return frame
        scale = max_dim / max(h, w)
        return cv2.resize(
            frame,
            (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_AREA,
        )

    @staticmethod
    def alpha_blend(
        background: np.ndarray, overlay: np.ndarray, alpha: float = 0.7
    ) -> np.ndarray:
        """
        Alpha-blend an overlay on top of a background frame.

        Useful for drawing semi-transparent panels or masks.
        Both arrays must be the same dtype (uint8).
        """
        if background.shape != overlay.shape:
            overlay = cv2.resize(
                overlay, (background.shape[1], background.shape[0])
            )
        return cv2.addWeighted(background, 1.0 - alpha, overlay, alpha, 0)
