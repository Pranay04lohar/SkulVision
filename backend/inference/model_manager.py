"""
Thread-safe model registry.

ModelManager owns all loaded runtimes and provides a centralized
interface for loading, caching, and unloading models. It prevents
duplicate loads of the same model across concurrent connections.

Usage:
    manager = get_model_manager()
    runtime = manager.load_onnx("yolo", "models/yolov8n.onnx", warmup_shape=(1,3,640,640))
    output = runtime.infer(some_input)
"""

from __future__ import annotations

import threading
from typing import Optional

from backend.core.config import get_settings
from backend.core.exceptions import ModelNotFoundError
from backend.core.logging_config import get_logger
from backend.inference.runtime import BaseInferenceRuntime, ONNXRuntime

logger = get_logger(__name__)


class ModelManager:
    """
    Centralised registry for inference runtimes.

    Thread-safe: a reentrant lock guards the internal model dict so
    concurrent WebSocket connections cannot trigger duplicate loads.
    """

    def __init__(self) -> None:
        self._models: dict[str, BaseInferenceRuntime] = {}
        self._lock = threading.RLock()
        self._settings = get_settings()

    def load_onnx(
        self,
        model_id: str,
        model_path: str,
        warmup_shape: Optional[tuple[int, ...]] = None,
    ) -> ONNXRuntime:
        """
        Load an ONNX model if not already cached and return its runtime.

        model_id    — stable key used to retrieve the runtime later
        model_path  — path to the .onnx file on disk
        warmup_shape — NCHW tuple for warmup pass, e.g. (1, 3, 640, 640)
        """
        with self._lock:
            if model_id in self._models:
                logger.debug("model_cache_hit", model_id=model_id)
                return self._models[model_id]  # type: ignore[return-value]

            logger.info("loading_model", model_id=model_id, path=model_path)

            runtime = ONNXRuntime(
                model_path=model_path,
                device=self._settings.DEVICE,
                num_threads=self._settings.NUM_INFERENCE_THREADS,
            )
            runtime.load()

            if warmup_shape is not None:
                logger.info("warming_up_model", model_id=model_id, shape=warmup_shape)
                runtime.warmup(warmup_shape)

            self._models[model_id] = runtime
            logger.info(
                "model_loaded",
                model_id=model_id,
                provider=runtime.active_provider,
            )
            return runtime

    def get(self, model_id: str) -> BaseInferenceRuntime:
        """Retrieve a previously loaded runtime. Raises if not found."""
        with self._lock:
            if model_id not in self._models:
                raise ModelNotFoundError(
                    f"Model '{model_id}' is not registered in ModelManager. "
                    "Ensure it was loaded during application startup."
                )
            return self._models[model_id]

    def is_loaded(self, model_id: str) -> bool:
        return model_id in self._models

    def unload(self, model_id: str) -> None:
        """Remove a model from the registry to free memory."""
        with self._lock:
            if model_id in self._models:
                del self._models[model_id]
                logger.info("model_unloaded", model_id=model_id)

    def loaded_models(self) -> list[str]:
        return list(self._models.keys())

    def __repr__(self) -> str:
        return f"ModelManager(loaded={self.loaded_models()})"


_model_manager: ModelManager | None = None


def get_model_manager() -> ModelManager:
    """Application-scoped singleton accessor."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager
