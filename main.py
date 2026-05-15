"""
SkulVision Backend — application entrypoint.

Startup sequence:
  1. Configure structured logging
  2. Create FastAPI application
  3. On lifespan start: initialize inference pipeline
  4. Inject WebSocket handler into router
  5. Serve via Uvicorn

Run development server:
    python main.py

Run with uvicorn directly (production):
    uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1

Note: workers must remain 1 for shared model state.
For horizontal scaling use separate processes with a load balancer
and move model weights to a shared volume or model registry.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.router import configure as configure_router
from backend.api.router import router
from backend.api.ws_handler import WebSocketHandler
from backend.core.config import get_settings
from backend.core.logging_config import configure_logging, get_logger
from backend.inference.model_manager import get_model_manager
from backend.pipeline.orchestrator import PipelineOrchestrator

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan manager.

    Everything before the yield runs at startup.
    Everything after the yield runs at shutdown.
    """
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)

    logger.info(
        "skul_vision_starting",
        version=settings.VERSION,
        device=settings.DEVICE,
        detection=settings.DETECTION_ENABLED,
        ocr=settings.OCR_ENABLED,
    )

    orchestrator = PipelineOrchestrator(model_manager=get_model_manager())
    await orchestrator.initialize()

    ws_handler = WebSocketHandler(orchestrator=orchestrator)
    configure_router(ws_handler)

    # Attach to app state so it's accessible in tests and middleware
    app.state.orchestrator = orchestrator
    app.state.ws_handler = ws_handler

    logger.info("skul_vision_ready", host=settings.HOST, port=settings.PORT)

    yield

    await orchestrator.shutdown()
    logger.info("skul_vision_stopped")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        description=(
            "SkulVision — real-time AI inference backend for a wearable HUD system. "
            "Accepts camera frames over WebSocket and returns HUD-annotated frames."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],   # tighten in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    return app


app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        # Workers must be 1 — model state is in-process
        workers=1,
    )
