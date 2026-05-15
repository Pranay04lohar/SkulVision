"""
Global application configuration.

All settings are readable from environment variables or a .env file.
Pydantic Settings v2 is used for validation and type coercion.
"""

from __future__ import annotations

from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = "SkulVision Backend"
    VERSION: str = "0.1.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # --- Inference Runtime ---
    INFERENCE_BACKEND: Literal["onnx", "tflite", "pytorch"] = "onnx"
    DEVICE: Literal["cpu", "cuda", "mps"] = "cpu"
    NUM_INFERENCE_THREADS: int = 4

    # --- Object Detection ---
    YOLO_MODEL_PATH: str = "models/yolov8n.onnx"
    YOLO_CONFIDENCE_THRESHOLD: float = 0.5
    YOLO_NMS_THRESHOLD: float = 0.45
    YOLO_INPUT_WIDTH: int = 640
    YOLO_INPUT_HEIGHT: int = 640
    DETECTION_ENABLED: bool = True

    # --- OCR ---
    OCR_ENGINE: Literal["easyocr", "paddleocr"] = "easyocr"
    OCR_LANGUAGES: str = "en"  # comma-separated, e.g. "en,hi"
    OCR_ENABLED: bool = True
    OCR_MIN_CONFIDENCE: float = 0.5
    # Minimum seconds between background OCR jobs (never blocks the video path)
    OCR_MIN_INTERVAL_SEC: float = 2.0
    # Downscale frame before EasyOCR (full-res OCR is ~10x slower on CPU)
    OCR_MAX_DIMENSION: int = 480
    # CLAHE + sharpen helps accuracy but costs ~20–40ms per frame
    OCR_ENHANCE: bool = False

    # --- Streaming ---
    MAX_FRAME_DIMENSION: int = 960
    TARGET_FPS: int = 20
    FRAME_QUEUE_SIZE: int = 5
    JPEG_QUALITY: int = 85

    # --- HUD / Overlay ---
    OVERLAY_ALPHA: float = 0.7
    OVERLAY_FONT_SCALE: float = 0.6
    OVERLAY_THICKNESS: int = 2
    HUD_STATS_FONT_SCALE: float = 0.58
    HUD_PANEL_ALPHA: float = 0.95
    # White stats card on video (FPS/DET/OCR) — off by default; blocks detection labels
    HUD_SHOW_STATS_PANEL: bool = False
    HUD_SHOW_FPS: bool = False
    HUD_SHOW_INFERENCE_TIME: bool = False

    @field_validator("YOLO_CONFIDENCE_THRESHOLD", "YOLO_NMS_THRESHOLD", "OVERLAY_ALPHA", "OCR_MIN_CONFIDENCE")
    @classmethod
    def validate_float_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Value must be between 0.0 and 1.0, got {v}")
        return v

    @field_validator("TARGET_FPS")
    @classmethod
    def validate_fps(cls, v: int) -> int:
        if not 1 <= v <= 120:
            raise ValueError(f"TARGET_FPS must be between 1 and 120, got {v}")
        return v

    @field_validator("OCR_MIN_INTERVAL_SEC")
    @classmethod
    def validate_ocr_interval_sec(cls, v: float) -> float:
        if v < 0.5:
            raise ValueError(f"OCR_MIN_INTERVAL_SEC must be >= 0.5, got {v}")
        return v

    @property
    def ocr_language_list(self) -> list[str]:
        return [lang.strip() for lang in self.OCR_LANGUAGES.split(",") if lang.strip()]

    @property
    def yolo_input_size(self) -> tuple[int, int]:
        """Returns (width, height)."""
        return (self.YOLO_INPUT_WIDTH, self.YOLO_INPUT_HEIGHT)


_settings: Settings | None = None


def get_settings() -> Settings:
    """Singleton accessor for application settings."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Clear cached settings (call on startup after .env is in place)."""
    global _settings
    _settings = None
