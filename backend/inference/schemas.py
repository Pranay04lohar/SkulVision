"""
Data transfer objects for the inference layer.

These are intentionally lightweight dataclasses — no Pydantic overhead
on the hot inference path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class InferenceInput:
    """Wraps a preprocessed numpy tensor ready for model inference."""

    data: np.ndarray
    input_name: str = "images"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class InferenceOutput:
    """Raw outputs returned from a model inference call."""

    data: list[np.ndarray]
    inference_time_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)
