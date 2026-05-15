"""
WebSocket message schemas for the streaming layer.

Binary messages carry raw frame bytes.
Text (JSON) messages follow the WSMessage envelope for control/status.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class MessageType(str, Enum):
    FRAME = "frame"
    RESULT = "result"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"
    CONFIG = "config"
    STATUS = "status"


class WSMessage(BaseModel):
    """Envelope for JSON control messages over the WebSocket channel."""

    type: MessageType
    payload: Optional[Any] = None
    client_id: Optional[str] = None
    timestamp: Optional[float] = None


class ResultPayload(BaseModel):
    """JSON summary sent back alongside (or instead of) a rendered frame."""

    frame_id: Optional[int] = None
    detection_count: int = 0
    ocr_region_count: int = 0
    detection_time_ms: float = 0.0
    ocr_time_ms: float = 0.0
    total_latency_ms: Optional[float] = None
    fps: float = 0.0


class ClientConfig(BaseModel):
    """Optional per-client config sent as a JSON message before streaming."""

    target_fps: Optional[int] = None
    enable_detection: Optional[bool] = None
    enable_ocr: Optional[bool] = None
    jpeg_quality: Optional[int] = None
