#!/usr/bin/env python3
"""
SkulVision model downloader / exporter.

YOLOv8 models are exported from Ultralytics to ONNX format.
The ultralytics package handles the PyTorch .pt download from their CDN
and conversion — no manual download URL needed.

Usage:
    python scripts/download_models.py              # exports yolov8n (default)
    python scripts/download_models.py --model yolov8s
    python scripts/download_models.py --list
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

MODELS_DIR = Path(__file__).parent.parent / "models"

AVAILABLE_MODELS: dict[str, dict] = {
    "yolov8n": {
        "description": "YOLOv8 Nano   — fastest  (~3ms/frame on CPU)",
        "pt_name":     "yolov8n.pt",
        "onnx_name":   "yolov8n.onnx",
    },
    "yolov8s": {
        "description": "YOLOv8 Small  — balanced (~7ms/frame on CPU)",
        "pt_name":     "yolov8s.pt",
        "onnx_name":   "yolov8s.onnx",
    },
    "yolov8m": {
        "description": "YOLOv8 Medium — accurate (~14ms/frame on CPU)",
        "pt_name":     "yolov8m.pt",
        "onnx_name":   "yolov8m.onnx",
    },
}


def export_model(model_name: str, imgsz: int = 640) -> None:
    info = AVAILABLE_MODELS[model_name]
    output_path = MODELS_DIR / info["onnx_name"]

    if output_path.exists():
        print(f"[SKIP] {info['onnx_name']} already exists at {output_path}")
        return

    print(f"[INFO] Exporting {model_name}: {info['description']}")
    print(f"       This will download the .pt weights on first run (~few MB).")

    # ultralytics CLI exports to <model_name>/ dir relative to cwd
    result = subprocess.run(
        [
            sys.executable, "-m", "ultralytics",
            "export",
            f"model={info['pt_name']}",
            "format=onnx",
            f"imgsz={imgsz}",
            "dynamic=false",
            "simplify=true",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"[ERROR] Export failed:\n{result.stderr}")
        sys.exit(1)

    # ultralytics saves to <name>.onnx relative to cwd
    exported = Path(info["pt_name"].replace(".pt", ".onnx"))
    if not exported.exists():
        # some versions nest inside a dir
        nested = Path(model_name) / info["onnx_name"]
        if nested.exists():
            exported = nested
        else:
            print(f"[ERROR] Could not find exported ONNX at {exported}")
            sys.exit(1)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.move(str(exported), str(output_path))
    print(f"[OK]   Saved to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export YOLOv8 models to ONNX for SkulVision inference"
    )
    parser.add_argument(
        "--model",
        choices=list(AVAILABLE_MODELS.keys()),
        default="yolov8n",
        help="Model variant to export (default: yolov8n)",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="Input image size for ONNX export (default: 640)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available models and exit",
    )
    args = parser.parse_args()

    if args.list:
        print("\nAvailable models:")
        for name, info in AVAILABLE_MODELS.items():
            onnx_path = MODELS_DIR / info["onnx_name"]
            status = "[downloaded]" if onnx_path.exists() else "[not downloaded]"
            print(f"  {name:12s}  {info['description']}  {status}")
        return

    export_model(args.model, imgsz=args.imgsz)


if __name__ == "__main__":
    main()
