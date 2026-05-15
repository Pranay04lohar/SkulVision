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

    # --- Streaming ---
    MAX_FRAME_DIMENSION: int = 1280
    TARGET_FPS: int = 20
    FRAME_QUEUE_SIZE: int = 5
    JPEG_QUALITY: int = 85

    # --- HUD / Overlay ---
    OVERLAY_ALPHA: float = 0.7
    OVERLAY_FONT_SCALE: float = 0.6
    OVERLAY_THICKNESS: int = 2
    HUD_SHOW_FPS: bool = True
    HUD_SHOW_INFERENCE_TIME: bool = True

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
