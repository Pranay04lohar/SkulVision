#!/usr/bin/env python3
"""
SkulVision camera test utility.

Modes:
  local   — open camera and display raw feed with FPS overlay (no server needed)
  stream  — open camera, stream frames to a running SkulVision server,
             display rendered HUD output

Usage:
    python scripts/test_camera.py                         # local webcam test
    python scripts/test_camera.py --mode stream           # stream to server
    python scripts/test_camera.py --source 0              # explicit camera index
    python scripts/test_camera.py --source path/to/video  # video file
    python scripts/test_camera.py --mode stream --server ws://192.168.1.10:8000/ws/stream
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time

import cv2
import numpy as np


def test_local(source: int | str = 0) -> None:
    """Display camera feed locally with FPS counter. No server required."""
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"[ERROR] Cannot open video source: {source}")
        sys.exit(1)

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    native_fps = cap.get(cv2.CAP_PROP_FPS)

    print(f"[OK]  Camera opened: {source}")
    print(f"      Resolution : {w}x{h}")
    print(f"      Native FPS : {native_fps}")
    print("      Press 'q' to quit.")

    frame_count = 0
    tick = time.time()
    display_fps = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[WARN] Failed to read frame — retrying...")
            continue

        frame_count += 1
        elapsed = time.time() - tick
        if elapsed >= 1.0:
            display_fps = frame_count / elapsed
            frame_count = 0
            tick = time.time()

        cv2.putText(frame, f"FPS: {display_fps:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.putText(frame, "SkulVision — Camera Test", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1, cv2.LINE_AA)

        cv2.imshow("SkulVision — Local Camera", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


async def stream_to_server(
    source: int | str = 0,
    server_url: str = "ws://localhost:8000/ws/stream",
    jpeg_quality: int = 85,
    target_fps: int = 20,
) -> None:
    """Stream camera frames to SkulVision server and display HUD output."""
    import websockets

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video source: {source}")
        return

    print(f"[INFO] Connecting to {server_url} ...")

    try:
        async with websockets.connect(
            server_url,
            max_size=10 * 1024 * 1024,   # 10 MB per message
            ping_interval=20,
            ping_timeout=10,
        ) as ws:
            print("[OK]  Connected to SkulVision backend.")
            print("      Press 'q' in the display window to quit.")

            stop_event = asyncio.Event()

            async def receive_loop() -> None:
                try:
                    async for message in ws:
                        if isinstance(message, bytes):
                            arr = np.frombuffer(message, dtype=np.uint8)
                            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                            if frame is not None:
                                cv2.imshow("SkulVision — HUD Output", frame)
                                if cv2.waitKey(1) & 0xFF == ord("q"):
                                    stop_event.set()
                                    return
                except Exception as exc:
                    print(f"[WARN] Receive error: {exc}")
                    stop_event.set()

            recv_task = asyncio.create_task(receive_loop())

            interval = 1.0 / target_fps
            while not stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    break

                _, buf = cv2.imencode(
                    ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]
                )
                try:
                    await ws.send(buf.tobytes())
                except Exception as exc:
                    print(f"[ERROR] Send failed: {exc}")
                    break

                await asyncio.sleep(interval)

            recv_task.cancel()
            try:
                await recv_task
            except asyncio.CancelledError:
                pass

    except (OSError, Exception) as exc:
        print(f"[ERROR] Could not connect to server: {exc}")
        print("        Make sure `python main.py` is running first.")
    finally:
        cap.release()
        cv2.destroyAllWindows()


def main() -> None:
    parser = argparse.ArgumentParser(description="SkulVision camera test utility")
    parser.add_argument(
        "--mode",
        choices=["local", "stream"],
        default="local",
        help="Test mode (default: local)",
    )
    parser.add_argument(
        "--source",
        default="0",
        help="Camera index (integer) or video file path (default: 0)",
    )
    parser.add_argument(
        "--server",
        default="ws://localhost:8000/ws/stream",
        help="WebSocket server URL for stream mode",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=20,
        help="Target send FPS for stream mode (default: 20)",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=85,
        help="JPEG quality for stream mode, 1-100 (default: 85)",
    )
    args = parser.parse_args()

    source: int | str = int(args.source) if args.source.isdigit() else args.source

    if args.mode == "local":
        test_local(source)
    else:
        asyncio.run(
            stream_to_server(
                source=source,
                server_url=args.server,
                jpeg_quality=args.quality,
                target_fps=args.fps,
            )
        )


if __name__ == "__main__":
    main()
