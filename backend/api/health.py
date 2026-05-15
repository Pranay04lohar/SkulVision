"""
Health check endpoints.

Provides a simple liveness and readiness probe suitable for
Docker health checks, load balancers, and monitoring systems.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.core.config import get_settings
from backend.inference.model_manager import get_model_manager

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    device: str
    loaded_models: list[str]
    detection_enabled: bool
    ocr_enabled: bool


@router.get("/", response_model=HealthResponse, summary="Liveness + readiness probe")
async def health_check() -> HealthResponse:
    """
    Returns service health including loaded models and active configuration.

    Status 'ok' means the server is live and models are loaded.
    """
    settings = get_settings()
    manager = get_model_manager()

    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        device=settings.DEVICE,
        loaded_models=manager.loaded_models(),
        detection_enabled=settings.DETECTION_ENABLED,
        ocr_enabled=settings.OCR_ENABLED,
    )
