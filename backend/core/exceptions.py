"""
SkulVision custom exception hierarchy.

All domain exceptions derive from SkulVisionBaseError so callers
can catch broadly or narrowly as needed.
"""

from __future__ import annotations


class SkulVisionBaseError(Exception):
    """Root exception for all SkulVision errors."""


class ModelNotFoundError(SkulVisionBaseError):
    """Raised when a required model file does not exist on disk."""


class InferenceError(SkulVisionBaseError):
    """Raised when a model inference call fails."""


class FrameProcessingError(SkulVisionBaseError):
    """Raised when a frame cannot be decoded or processed."""


class StreamingError(SkulVisionBaseError):
    """Raised when the WebSocket streaming layer encounters an error."""


class OCRError(SkulVisionBaseError):
    """Raised when OCR extraction fails."""


class OverlayError(SkulVisionBaseError):
    """Raised when HUD overlay rendering fails."""


class ConfigurationError(SkulVisionBaseError):
    """Raised when the application is misconfigured."""


class PipelineNotInitializedError(SkulVisionBaseError):
    """Raised when the inference pipeline is used before initialization."""
