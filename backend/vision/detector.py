"""
YOLOv8 object detector.

Wraps an ONNX-exported YOLOv8 model and exposes a clean detect() API.
Handles the full postprocessing pipeline:
  raw tensor → confidence filter → NMS → original-space bounding boxes

YOLOv8 ONNX output format:
  Shape: [1, 84, num_anchors]
  Channels: 4 (xywh center-format) + 80 (COCO class scores)

Export a model with:
  yolo export model=yolov8n.pt format=onnx imgsz=640
"""

from __future__ import annotations

import cv2
import numpy as np

from backend.core.config import get_settings
from backend.core.exceptions import InferenceError, PipelineNotInitializedError
from backend.core.logging_config import get_logger
from backend.inference.model_manager import ModelManager
from backend.inference.schemas import InferenceInput
from backend.vision.preprocessor import VisionPreprocessor
from backend.vision.schemas import BoundingBox, Detection, DetectionFrame

logger = get_logger(__name__)

# COCO 80-class labels — must match the order used during training
COCO_CLASSES: list[str] = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep",
    "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
    "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
    "sports ball", "kite", "baseball bat", "baseball glove", "skateboard",
    "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork",
    "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv",
    "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave",
    "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
    "scissors", "teddy bear", "hair drier", "toothbrush",
]


class YOLODetector:
    """
    YOLOv8 detector backed by ONNX Runtime.

    Thread-safety: instances are NOT shared across threads.
    Each WebSocket connection should either serialize calls or
    use a dedicated instance. For Phase 1, the async executor
    serializes per-client anyway.
    """

    MODEL_ID = "yolov8_detector"

    def __init__(self, model_manager: ModelManager) -> None:
        self._settings = get_settings()
        self._model_manager = model_manager
        self._preprocessor = VisionPreprocessor(
            input_size=self._settings.yolo_input_size
        )
        self._runtime = None

    def load(self) -> None:
        """Load YOLO ONNX model via ModelManager (idempotent)."""
        w, h = self._settings.yolo_input_size
        warmup_shape = (1, 3, h, w)  # NCHW

        self._runtime = self._model_manager.load_onnx(
            model_id=self.MODEL_ID,
            model_path=self._settings.YOLO_MODEL_PATH,
            warmup_shape=warmup_shape,
        )
        logger.info(
            "yolo_detector_ready",
            model=self._settings.YOLO_MODEL_PATH,
            input_size=self._settings.yolo_input_size,
        )

    def detect(self, frame: np.ndarray) -> DetectionFrame:
        """
        Run detection on a single BGR frame.

        Parameters
        ----------
        frame : np.ndarray
            BGR image from OpenCV in HWC format.

        Returns
        -------
        DetectionFrame with all post-NMS detections.
        """
        if self._runtime is None:
            raise PipelineNotInitializedError(
                "YOLODetector not loaded. Call load() first."
            )

        original_h, original_w = frame.shape[:2]
        blob, scale_x, scale_y, pad_x, pad_y = self._preprocessor.preprocess(frame)

        inference_out = self._runtime.infer(
            InferenceInput(data=blob, input_name="images")
        )

        # YOLOv8 outputs a single tensor [1, 84, N]
        raw = inference_out.data[0]

        detections = self._postprocess(
            raw, scale_x, scale_y, pad_x, pad_y, original_w, original_h
        )

        return DetectionFrame(
            detections=detections,
            inference_time_ms=inference_out.inference_time_ms,
            frame_width=original_w,
            frame_height=original_h,
        )

    # ------------------------------------------------------------------
    # Internal postprocessing
    # ------------------------------------------------------------------

    def _postprocess(
        self,
        raw: np.ndarray,
        scale_x: float,
        scale_y: float,
        pad_x: int,
        pad_y: int,
        original_w: int,
        original_h: int,
    ) -> list[Detection]:
        # raw: [1, 84, num_anchors] → transpose to [num_anchors, 84]
        predictions = raw[0].T

        boxes_xywh = predictions[:, :4]     # center-format
        class_scores = predictions[:, 4:]   # 80 class logits

        class_ids = np.argmax(class_scores, axis=1)
        confidences = class_scores[np.arange(len(class_scores)), class_ids]

        # Confidence filter
        mask = confidences >= self._settings.YOLO_CONFIDENCE_THRESHOLD
        if not mask.any():
            return []

        boxes_xywh = boxes_xywh[mask]
        confidences = confidences[mask]
        class_ids = class_ids[mask]

        # xywh (center) → xyxy
        x1 = boxes_xywh[:, 0] - boxes_xywh[:, 2] / 2.0
        y1 = boxes_xywh[:, 1] - boxes_xywh[:, 3] / 2.0
        x2 = boxes_xywh[:, 0] + boxes_xywh[:, 2] / 2.0
        y2 = boxes_xywh[:, 1] + boxes_xywh[:, 3] / 2.0
        boxes_xyxy = np.stack([x1, y1, x2, y2], axis=1)

        # Map from letterboxed tensor space → original frame space
        boxes_xyxy = self._preprocessor.decode_boxes(
            boxes_xyxy, scale_x, scale_y, pad_x, pad_y, original_w, original_h
        )

        # Convert to xywh for cv2.dnn.NMSBoxes
        nms_boxes = boxes_xyxy.copy()
        nms_boxes[:, 2] -= nms_boxes[:, 0]
        nms_boxes[:, 3] -= nms_boxes[:, 1]

        indices = cv2.dnn.NMSBoxes(
            nms_boxes.tolist(),
            confidences.tolist(),
            self._settings.YOLO_CONFIDENCE_THRESHOLD,
            self._settings.YOLO_NMS_THRESHOLD,
        )

        detections: list[Detection] = []
        for idx in indices:
            i = int(idx)
            cid = int(class_ids[i])
            detections.append(
                Detection(
                    class_id=cid,
                    class_name=(
                        COCO_CLASSES[cid] if cid < len(COCO_CLASSES) else f"cls_{cid}"
                    ),
                    confidence=float(confidences[i]),
                    bbox=BoundingBox(
                        x1=float(boxes_xyxy[i, 0]),
                        y1=float(boxes_xyxy[i, 1]),
                        x2=float(boxes_xyxy[i, 2]),
                        y2=float(boxes_xyxy[i, 3]),
                    ),
                )
            )

        return detections
