"""
Inference runtime abstraction.

Architecture:
  BaseInferenceRuntime  — abstract interface, backend-agnostic
  ONNXRuntime           — ONNX Runtime implementation (CPU / CUDA / CoreML)

Adding a new backend (TFLite, PyTorch, TensorRT, etc.) means implementing
BaseInferenceRuntime without touching any downstream code.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np

from backend.core.exceptions import InferenceError, ModelNotFoundError
from backend.inference.schemas import InferenceInput, InferenceOutput


class BaseInferenceRuntime(ABC):
    """
    Abstract base class for all inference runtimes.

    Subclasses must implement: load(), infer(), warmup()
    """

    def __init__(self, model_path: str, device: str = "cpu", num_threads: int = 4) -> None:
        self.model_path = Path(model_path)
        self.device = device
        self.num_threads = num_threads
        self._loaded = False

        if not self.model_path.exists():
            raise ModelNotFoundError(
                f"Model file not found: {self.model_path.resolve()}\n"
                "Run: python scripts/download_models.py"
            )

    @abstractmethod
    def load(self) -> None:
        """Load model weights into memory and prepare for inference."""
        ...

    @abstractmethod
    def infer(self, inputs: InferenceInput) -> InferenceOutput:
        """Execute a single forward pass. Thread-safety is caller responsibility."""
        ...

    @abstractmethod
    def warmup(self, input_shape: tuple[int, ...]) -> None:
        """
        Run a few dummy inferences to initialize GPU kernels / JIT caches.
        Critical for accurate first-frame latency measurements.
        """
        ...

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"model={self.model_path.name}, "
            f"device={self.device}, "
            f"loaded={self._loaded})"
        )


class ONNXRuntime(BaseInferenceRuntime):
    """
    ONNX Runtime inference backend.

    Provider selection:
      cuda  → CUDAExecutionProvider → CPUExecutionProvider
      mps   → CoreMLExecutionProvider → CPUExecutionProvider
      cpu   → CPUExecutionProvider

    Graph optimizations are set to ORT_ENABLE_ALL for maximum throughput.
    """

    def __init__(self, model_path: str, device: str = "cpu", num_threads: int = 4) -> None:
        super().__init__(model_path, device, num_threads)
        self._session: Any = None
        self._input_names: list[str] = []
        self._output_names: list[str] = []

    def load(self) -> None:
        import onnxruntime as ort

        options = ort.SessionOptions()
        options.inter_op_num_threads = self.num_threads
        options.intra_op_num_threads = self.num_threads
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        # Suppress ONNX Runtime verbose output
        options.log_severity_level = 3

        providers = self._resolve_providers()

        self._session = ort.InferenceSession(
            str(self.model_path),
            sess_options=options,
            providers=providers,
        )

        self._input_names = [inp.name for inp in self._session.get_inputs()]
        self._output_names = [out.name for out in self._session.get_outputs()]
        self._loaded = True

    def infer(self, inputs: InferenceInput) -> InferenceOutput:
        if not self._loaded or self._session is None:
            raise InferenceError("Runtime not loaded. Call load() first.")

        feed = {inputs.input_name: inputs.data}

        t0 = time.perf_counter()
        try:
            raw_outputs = self._session.run(self._output_names, feed)
        except Exception as exc:
            raise InferenceError(f"ONNX inference failed: {exc}") from exc
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        return InferenceOutput(data=raw_outputs, inference_time_ms=elapsed_ms)

    def warmup(self, input_shape: tuple[int, ...]) -> None:
        dummy_input = InferenceInput(
            data=np.zeros(input_shape, dtype=np.float32),
            input_name=self._input_names[0] if self._input_names else "images",
        )
        for _ in range(3):
            self.infer(dummy_input)

    def _resolve_providers(self) -> list[str]:
        import onnxruntime as ort

        available = ort.get_available_providers()

        if self.device == "cuda" and "CUDAExecutionProvider" in available:
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]
        if self.device == "mps" and "CoreMLExecutionProvider" in available:
            return ["CoreMLExecutionProvider", "CPUExecutionProvider"]
        return ["CPUExecutionProvider"]

    @property
    def input_names(self) -> list[str]:
        return self._input_names

    @property
    def output_names(self) -> list[str]:
        return self._output_names

    @property
    def active_provider(self) -> str | None:
        if self._session is None:
            return None
        providers = self._session.get_providers()
        return providers[0] if providers else None
