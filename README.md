# SkulVision

**AI-powered wearable HUD system — Phase 1: Core Prototype Foundation**

> "Phone is the brain. Glasses are the eyes and display."

SkulVision is a real-time visual intelligence system for wearable heads-up displays. The phone handles all AI inference; the glasses act as camera input and HUD display. This repository contains the backend inference server built for Phase 1.

---

## Table of Contents

- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Module Reference](#module-reference)
- [Data Flow](#data-flow)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Scripts](#scripts)
- [Running Tests](#running-tests)
- [Performance Targets](#performance-targets)
- [Roadmap](#roadmap)
- [Engineering Principles](#engineering-principles)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     SkulVision Backend                        │
│                                                              │
│  WebSocket /ws/stream                                        │
│       │                                                      │
│  WebSocketHandler                                            │
│  ├── receive_loop  ──▶  FrameProcessor.submit_frame()        │
│  │                            │  (bounded async queue)       │
│  └── send_loop    ◀──  FrameProcessor.next_result()          │
│                               │                              │
│                    PipelineOrchestrator.process_frame()      │
│                    │                                         │
│                    ├── Stage 1: YOLODetector        ──┐      │
│                    ├── Stage 2: EasyOCREngine        ─┤ ThreadPoolExecutor
│                    └── Stage 3: HUDRenderer          ─┘      │
│                               │                              │
│                    FrameCompositor.encode_jpeg()             │
│                               │                              │
│              Rendered JPEG bytes → Client                    │
└──────────────────────────────────────────────────────────────┘
```

**Hardware model:**
- **Smartphone** — runs this backend (all AI inference)
- **Glasses** — camera module (sends frames) + HUD display (receives rendered frames)
- **Protocol** — WebSocket binary streaming, JPEG frames

---

## Project Structure

```
SkulVision/
│
├── main.py                         # FastAPI application entrypoint
├── requirements.txt                # Python dependencies
├── pytest.ini                      # Test configuration
├── .env.example                    # Environment variable template
├── .gitignore
│
├── backend/
│   ├── core/                       # Global config, logging, exceptions
│   │   ├── config.py               # Pydantic Settings — all env vars
│   │   ├── logging_config.py       # Structlog structured logging
│   │   └── exceptions.py           # Typed exception hierarchy
│   │
│   ├── inference/                  # Runtime abstraction layer
│   │   ├── runtime.py              # BaseInferenceRuntime + ONNXRuntime
│   │   ├── model_manager.py        # Thread-safe model registry (singleton)
│   │   └── schemas.py              # InferenceInput / InferenceOutput
│   │
│   ├── vision/                     # Object detection pipeline
│   │   ├── detector.py             # YOLOv8 ONNX detector
│   │   ├── preprocessor.py         # Letterbox resize + coordinate recovery
│   │   └── schemas.py              # BoundingBox, Detection, DetectionFrame
│   │
│   ├── ocr/                        # Text extraction pipeline
│   │   ├── engine.py               # EasyOCR wrapper
│   │   ├── preprocessor.py         # CLAHE + sharpening for OCR
│   │   └── schemas.py              # TextRegion, OCRFrame
│   │
│   ├── overlay/                    # HUD rendering
│   │   ├── renderer.py             # OpenCV HUD renderer (boxes, labels, stats)
│   │   ├── compositor.py           # JPEG encode/decode, resize, alpha blend
│   │   └── schemas.py              # Color palette, OverlayConfig, RenderResult
│   │
│   ├── pipeline/                   # Orchestration
│   │   ├── orchestrator.py         # 3-stage async pipeline coordinator
│   │   └── context.py              # FrameContext — unit of work per frame
│   │
│   ├── streaming/                  # WebSocket layer
│   │   ├── frame_processor.py      # Per-client queue + pipeline bridge
│   │   └── schemas.py              # WSMessage, ResultPayload, ClientConfig
│   │
│   ├── api/                        # FastAPI routes
│   │   ├── router.py               # Central router + WebSocket endpoint
│   │   ├── ws_handler.py           # WebSocket session lifecycle
│   │   └── health.py               # GET /health liveness probe
│   │
│   └── sensors/                    # IMU / sensor relay (Phase 2+)
│
├── models/                         # ONNX / TFLite model files (gitignored)
│   └── .gitkeep
│
├── scripts/
│   ├── download_models.py          # Export YOLOv8 to ONNX via ultralytics
│   └── test_camera.py              # Local camera test + WebSocket stream test
│
└── tests/
    ├── test_vision.py              # BoundingBox math, preprocessor, DetectionFrame
    ├── test_ocr.py                 # OCRPreprocessor, TextRegion, OCRFrame
    └── test_pipeline.py            # FrameContext lifecycle, FrameCompositor
```

---

## Module Reference

### `backend/core`

| File | Purpose |
|---|---|
| `config.py` | All configuration via `Settings(BaseSettings)`. Read from `.env` or env vars. Access via `get_settings()`. |
| `logging_config.py` | Structlog setup. TTY → colored console output. Non-TTY → JSON lines. Call `configure_logging()` at startup. |
| `exceptions.py` | Exception hierarchy rooted at `SkulVisionBaseError`. Catch broadly or narrowly as needed. |

### `backend/inference`

| File | Purpose |
|---|---|
| `runtime.py` | `BaseInferenceRuntime` abstract base + `ONNXRuntime` implementation. Adding TFLite/TensorRT = new subclass only. |
| `model_manager.py` | `ModelManager` singleton with `RLock`. Prevents duplicate model loads across concurrent WebSocket connections. |
| `schemas.py` | `InferenceInput` / `InferenceOutput` dataclasses. Lightweight — no Pydantic overhead on the hot inference path. |

### `backend/vision`

| File | Purpose |
|---|---|
| `preprocessor.py` | Letterbox resize preserving aspect ratio. Returns blob + scale/padding factors needed to recover original-space coordinates. |
| `detector.py` | `YOLODetector` — full pipeline from raw frame to `DetectionFrame`. YOLOv8 ONNX output format `[1, 84, N]` → NMS → `Detection` list. |
| `schemas.py` | `BoundingBox` with geometric properties. `Detection` with class/confidence. `DetectionFrame` with filter helpers. |

### `backend/ocr`

| File | Purpose |
|---|---|
| `preprocessor.py` | CLAHE adaptive contrast + unsharp mask. Perspective-correct quad crop for rotated text regions. |
| `engine.py` | `EasyOCREngine` — lazy-loaded, GPU-aware. Filters results by `OCR_MIN_CONFIDENCE`. Phase 2 hook: swap for `PaddleOCREngine` without changing callers. |
| `schemas.py` | `TextRegion` with quad `bbox_points` (not AABB — handles rotated text). `OCRFrame` with confidence filter. |

### `backend/overlay`

| File | Purpose |
|---|---|
| `schemas.py` | `Color(b,g,r)` dataclass. `PALETTE` dict with semantic names (`detection_box`, `ocr_text`, `hud_primary`, etc.). `OverlayConfig`. |
| `renderer.py` | `HUDRenderer` — draws detection boxes + labels, OCR quad outlines + text, top-left stats panel. Tracks real FPS across frames. |
| `compositor.py` | Static utilities: JPEG encode/decode, max-dimension resize, alpha blend. Used everywhere encoding/decoding is needed. |

### `backend/pipeline`

| File | Purpose |
|---|---|
| `context.py` | `FrameContext` carries `raw_frame`, `detection_result`, `ocr_result`, `rendered_frame`, timing, and routing metadata through all pipeline stages. |
| `orchestrator.py` | `PipelineOrchestrator` — initializes models on startup, runs 3 stages per frame via `ThreadPoolExecutor(max_workers=1)`. Graceful per-stage failure handling. |

### `backend/streaming`

| File | Purpose |
|---|---|
| `frame_processor.py` | `FrameProcessor` — bounded `asyncio.Queue` per client. Drops frames under backpressure (correct real-time behavior). Tracks dropped frame count. |
| `schemas.py` | `WSMessage` envelope for JSON control messages. `ResultPayload`, `ClientConfig` Pydantic models. |

### `backend/api`

| File | Purpose |
|---|---|
| `health.py` | `GET /health` — returns status, version, device, loaded models. Suitable for Docker `HEALTHCHECK` and load balancer probes. |
| `ws_handler.py` | `WebSocketHandler` — manages full WS session lifecycle. Receive and send loops run concurrently via `asyncio.gather`-style `wait`. |
| `router.py` | Central `APIRouter`. Aggregates sub-routers. WebSocket handler injected at startup via `configure()` — no import-time side effects. |

---

## Data Flow

**One frame, end-to-end:**

```
1.  Client (glasses / test script) opens WS connection to /ws/stream

2.  Client sends raw JPEG bytes  →  WebSocketHandler._receive_loop()
                                          ↓
3.                                   FrameProcessor.submit_frame()
                                     [dropped if queue full — backpressure]
                                          ↓
4.  WebSocketHandler._send_loop() polls  FrameProcessor.next_result()
                                          ↓
5.                                   FrameCompositor.decode_frame()    [bytes → numpy BGR]
                                   + FrameCompositor.resize_max_dimension()
                                          ↓
6.                                   PipelineOrchestrator.make_context()  [FrameContext]
                                          ↓
7.  Stage 1 (ThreadPoolExecutor)     YOLODetector.detect()
                                     → DetectionFrame [N detections, inference_time_ms]
                                          ↓
8.  Stage 2 (ThreadPoolExecutor)     EasyOCREngine.extract()
                                     → OCRFrame [M text regions, inference_time_ms]
                                          ↓
9.  Stage 3 (sync, fast)             HUDRenderer.render()
                                     → draws boxes, labels, OCR quads, stats panel
                                          ↓
10.                                  FrameCompositor.encode_jpeg()    [numpy → bytes]
                                          ↓
11. Client receives rendered JPEG bytes (HUD-overlaid frame)
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- A webcam or video file (for testing)
- 4 GB RAM minimum (8 GB recommended for OCR + detection simultaneously)

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

For GPU acceleration (CUDA), replace the ONNX and PyTorch lines:

```bash
pip install onnxruntime-gpu
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

### 2. Export the YOLO model

```bash
# Default: yolov8n (fastest)
python scripts/download_models.py

# For higher accuracy
python scripts/download_models.py --model yolov8s

# List all available variants
python scripts/download_models.py --list
```

This downloads the `.pt` weights from Ultralytics CDN and exports them to `models/yolov8n.onnx`.

### 3. Configure environment

```bash
copy .env.example .env
# Edit .env as needed — defaults work out of the box
```

### 4. Start the server

```bash
python main.py
```

Server starts at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### 5. Test with your webcam

```bash
# Local camera test (no server needed)
python scripts/test_camera.py

# Stream to server and view HUD output (server must be running)
python scripts/test_camera.py --mode stream
```

---

## Configuration

All settings are read from `.env` or environment variables. See `.env.example` for the full list.

| Variable | Default | Description |
|---|---|---|
| `DEVICE` | `cpu` | Inference device: `cpu`, `cuda`, `mps` |
| `YOLO_MODEL_PATH` | `models/yolov8n.onnx` | Path to exported ONNX model |
| `YOLO_CONFIDENCE_THRESHOLD` | `0.5` | Minimum detection confidence |
| `YOLO_NMS_THRESHOLD` | `0.45` | NMS IoU threshold |
| `YOLO_INPUT_WIDTH/HEIGHT` | `640` | Model input resolution |
| `DETECTION_ENABLED` | `true` | Toggle object detection stage |
| `OCR_ENGINE` | `easyocr` | OCR backend: `easyocr` or `paddleocr` |
| `OCR_LANGUAGES` | `en` | Comma-separated language codes |
| `OCR_ENABLED` | `true` | Toggle OCR stage |
| `OCR_MIN_CONFIDENCE` | `0.5` | Minimum OCR confidence |
| `TARGET_FPS` | `20` | WebSocket send rate |
| `FRAME_QUEUE_SIZE` | `5` | Per-client frame queue depth |
| `MAX_FRAME_DIMENSION` | `1280` | Max frame side before inference |
| `JPEG_QUALITY` | `85` | Output JPEG compression quality |

---

## API Reference

### `GET /health`

Returns server status and loaded model info.

```json
{
  "status": "ok",
  "version": "0.1.0",
  "device": "cpu",
  "loaded_models": ["yolov8_detector"],
  "detection_enabled": true,
  "ocr_enabled": true
}
```

### `WS /ws/stream`

Main streaming endpoint.

**Client → Server:** Raw JPEG bytes (one camera frame per message)

**Server → Client:** Raw JPEG bytes (rendered HUD frame)

The server paces output at `TARGET_FPS`. Excess incoming frames are dropped under backpressure — the most recent frame in the queue always wins.

---

## Scripts

### `scripts/download_models.py`

Exports YOLOv8 weights to ONNX format using the `ultralytics` CLI.

```bash
python scripts/download_models.py --model yolov8n   # default
python scripts/download_models.py --model yolov8s   # higher accuracy
python scripts/download_models.py --list            # see all options
```

### `scripts/test_camera.py`

Camera test and WebSocket stream utility.

```bash
# Local test — no server needed
python scripts/test_camera.py

# Stream to server
python scripts/test_camera.py --mode stream

# Options
python scripts/test_camera.py --source 1            # camera index 1
python scripts/test_camera.py --source video.mp4    # video file
python scripts/test_camera.py --mode stream --server ws://192.168.1.10:8000/ws/stream
python scripts/test_camera.py --mode stream --fps 15 --quality 75
```

---

## Running Tests

Tests are pure unit tests — no model files, GPU, or camera required.

```bash
pytest
```

```
tests/test_vision.py    — BoundingBox geometry, letterbox preprocessor, DetectionFrame filters
tests/test_ocr.py       — OCR preprocessor CLAHE/crop, TextRegion/OCRFrame schemas
tests/test_pipeline.py  — FrameContext lifecycle, FrameCompositor encode/decode roundtrip
```

---

## Performance Targets

| Phase | FPS Target | Status |
|---|---|---|
| Phase 1 — Prototype | 15–20 FPS | Current |
| Phase 2 — Optimized | 24–30 FPS | Planned |
| Phase 3 — Aspirational | 60 FPS | Future |

**Typical latency breakdown (CPU, 640×480 input, yolov8n):**

| Stage | Approximate time |
|---|---|
| Frame decode + resize | ~2 ms |
| YOLOv8n ONNX inference | ~25–40 ms |
| EasyOCR inference | ~80–200 ms |
| HUD rendering (OpenCV) | ~1–2 ms |
| JPEG encode | ~3–5 ms |

For real-time performance at 20 FPS, run detection and OCR on alternate frames, or disable OCR and enable it only when text regions are detected.

---

## Roadmap

### Phase 1 — Core Prototype Foundation (current)
- [x] WebSocket streaming server
- [x] YOLOv8 ONNX object detection
- [x] EasyOCR text extraction
- [x] OpenCV HUD renderer
- [x] Async pipeline with backpressure
- [x] Modular, typed architecture

### Phase 2 — Intelligence Layer
- [ ] Signboard translation (on-device lightweight model)
- [ ] Mathematical equation solver
- [ ] Scene context generation
- [ ] Voice interaction (Whisper)
- [ ] Object tracking (ByteTrack / SORT)
- [ ] PaddleOCR engine option
- [ ] IMU sensor relay from glasses

### Phase 3 — Spatial Intelligence
- [ ] SLAM integration
- [ ] Environmental mapping
- [ ] Agentic AI assistant
- [ ] WebRTC for lower-latency streaming
- [ ] Multi-modal scene understanding
- [ ] Edge TPU / Jetson deployment

---

## Engineering Principles

**Runtime abstraction** — `BaseInferenceRuntime` decouples every AI module from the underlying framework. Adding TFLite, TensorRT, or CoreML is a new subclass, not a rewrite.

**FrameContext as unit of work** — each frame travels as a single object through all stages. Adding a Stage 4 (e.g. translation) means appending to the orchestrator, not refactoring callers.

**Backpressure via bounded queue** — real-time systems must drop stale data, not buffer it. The per-client `asyncio.Queue` with a fixed depth ensures memory is bounded and output is always fresh.

**ThreadPoolExecutor(max_workers=1)** — ONNX Runtime sessions are serialized safely without locks. Upgrade path: `ProcessPoolExecutor` for true multicore when models support it.

**Graceful stage degradation** — each pipeline stage catches its own exceptions. A crashing OCR model does not kill detection or HUD rendering; the rendered frame is still returned without OCR annotations.

**Zero import-time side effects** — models are loaded in the FastAPI lifespan, not at module import. This keeps startup predictable and test imports fast.
