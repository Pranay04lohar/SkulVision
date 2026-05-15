"""
EasyOCR-based text extraction engine.

Design decisions:
  - Lazy-loaded: model download + GPU init happens once on first load(),
    not at import time (keeps startup fast when OCR is disabled).
  - GPU usage automatically follows the DEVICE setting.
  - Confidence threshold filtering is applied before returning results
    to avoid passing garbage text to the overlay renderer.
  - Thread-safety: EasyOCR's Reader uses its own internal locking, but
    we serialize calls via the async executor in the pipeline anyway.

Phase 2 hook: swap EasyOCREngine for PaddleOCREngine without changing
any downstream code — both implement the same extract() interface.
"""

from __future__ import annotations

import time
from typing import Any

import cv2
import numpy as np

from backend.core.config import get_settings
from backend.core.exceptions import OCRError, PipelineNotInitializedError
from backend.core.logging_config import get_logger
from backend.ocr.preprocessor import OCRPreprocessor
from backend.ocr.schemas import OCRFrame, TextRegion

logger = get_logger(__name__)


class EasyOCREngine:
    """
    EasyOCR wrapper for in-frame text extraction.

    Extraction flow:
      1. Optionally enhance frame with CLAHE + sharpening
      2. Feed to easyocr.Reader.readtext()
      3. Filter results by min_confidence
      4. Return structured OCRFrame
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._reader: Any = None
        self._preprocessor = OCRPreprocessor()
        self._loaded = False

    def load(self) -> None:
        """
        Download language models (first run) and initialise the reader.
        Models are cached to ~/.EasyOCR/ by the library after first download.
        """
        import easyocr

        gpu = self._settings.DEVICE == "cuda"
        logger.info(
            "loading_easyocr",
            languages=self._settings.ocr_language_list,
            gpu=gpu,
        )

        self._reader = easyocr.Reader(
            lang_list=self._settings.ocr_language_list,
            gpu=gpu,
        )
        self._loaded = True
        logger.info("easyocr_ready", languages=self._settings.ocr_language_list)

    def extract(self, frame: np.ndarray, enhance: bool = True) -> OCRFrame:
        """
        Extract all readable text from a BGR frame.

        Parameters
        ----------
        frame   : BGR numpy array
        enhance : whether to apply CLAHE + sharpening before OCR

        Returns
        -------
        OCRFrame with all text regions above the confidence threshold
        """
        if not self._loaded or self._reader is None:
            raise PipelineNotInitializedError(
                "EasyOCR not loaded. Call load() first."
            )

        use_enhance = enhance and self._settings.OCR_ENHANCE
        processed = self._preprocessor.enhance_for_ocr(frame) if use_enhance else frame
        ocr_frame, coord_scale = self._downscale_for_ocr(processed)

        t0 = time.perf_counter()
        try:
            raw_results = self._reader.readtext(
                ocr_frame,
                paragraph=False,
                batch_size=1,
            )
        except Exception as exc:
            raise OCRError(f"EasyOCR inference failed: {exc}") from exc
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        regions: list[TextRegion] = []
        for bbox, text, confidence in raw_results:
            if float(confidence) < self._settings.OCR_MIN_CONFIDENCE:
                continue
            if not text.strip():
                continue
            points = [[float(p[0]) * coord_scale, float(p[1]) * coord_scale] for p in bbox]
            regions.append(
                TextRegion(
                    text=text.strip(),
                    confidence=float(confidence),
                    bbox_points=points,
                )
            )

        return OCRFrame(regions=regions, inference_time_ms=elapsed_ms)

    def _downscale_for_ocr(self, frame: np.ndarray) -> tuple[np.ndarray, float]:
        """
        Resize for OCR inference; return frame and multiplier to map boxes
        back to original pixel coordinates.
        """
        max_dim = self._settings.OCR_MAX_DIMENSION
        h, w = frame.shape[:2]
        longest = max(h, w)
        if longest <= max_dim:
            return frame, 1.0

        scale = max_dim / longest
        new_w = int(w * scale)
        new_h = int(h * scale)
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized, 1.0 / scale

    @property
    def is_loaded(self) -> bool:
        return self._loaded
