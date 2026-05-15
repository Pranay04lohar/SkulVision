import { useCallback, useEffect, useRef, useState, type RefObject } from "react";

import type { HudCameraHandle } from "../camera/types";
import { TARGET_CAPTURE_FPS } from "../config";
import { ConnectionState, SkulVisionSocket } from "../services/skulVisionSocket";
import { sleep } from "../utils/bytes";

const FRAME_INTERVAL_MS = Math.ceil(1000 / TARGET_CAPTURE_FPS);

export function useHudStream(cameraRef: RefObject<HudCameraHandle | null>) {
  const socketRef = useRef<SkulVisionSocket | null>(null);
  const streamingRef = useRef(false);
  const wantStreamRef = useRef(false);
  const framesSentRef = useRef(0);
  const sentInWindowRef = useRef(0);
  const windowStartRef = useRef(Date.now());

  const [serverHost, setServerHost] = useState("");
  const [connectionState, setConnectionState] = useState<ConnectionState>("idle");
  const [statusMessage, setStatusMessage] = useState("");
  const [hudUri, setHudUri] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [framesSent, setFramesSent] = useState(0);
  const [captureFps, setCaptureFps] = useState(0);

  const bumpFpsCounter = useCallback(() => {
    sentInWindowRef.current += 1;
    framesSentRef.current += 1;

    const now = Date.now();
    const elapsed = now - windowStartRef.current;
    if (elapsed >= 1000) {
      setCaptureFps(sentInWindowRef.current / (elapsed / 1000));
      setFramesSent(framesSentRef.current);
      sentInWindowRef.current = 0;
      windowStartRef.current = now;
    }
  }, []);

  useEffect(() => {
    const socket = new SkulVisionSocket();
    socketRef.current = socket;

    socket.setHudHandler(setHudUri);
    socket.setStateHandler((state, message) => {
      setConnectionState(state);
      if (message) setStatusMessage(message);
      if (state !== "connected") {
        setIsStreaming(false);
        streamingRef.current = false;
      }
    });

    return () => {
      streamingRef.current = false;
      socket.disconnect();
      socketRef.current = null;
    };
  }, []);

  const connect = useCallback(async (host: string) => {
    setStatusMessage("");
    setHudUri(null);
    framesSentRef.current = 0;
    sentInWindowRef.current = 0;
    windowStartRef.current = Date.now();
    setFramesSent(0);
    setCaptureFps(0);
    await socketRef.current?.connect(host);
  }, []);

  const disconnect = useCallback(() => {
    wantStreamRef.current = false;
    streamingRef.current = false;
    setIsStreaming(false);
    socketRef.current?.disconnect();
    setHudUri(null);
  }, []);

  const startStreaming = useCallback(() => {
    if (connectionState !== "connected") return;
    wantStreamRef.current = true;
    if (!cameraReady) {
      setStatusMessage("Waiting for camera…");
      return;
    }
    streamingRef.current = true;
    setIsStreaming(true);
    setStatusMessage("");
  }, [connectionState, cameraReady]);

  const stopStreaming = useCallback(() => {
    wantStreamRef.current = false;
    streamingRef.current = false;
    setIsStreaming(false);
  }, []);

  useEffect(() => {
    if (
      wantStreamRef.current &&
      cameraReady &&
      connectionState === "connected" &&
      !isStreaming
    ) {
      streamingRef.current = true;
      setIsStreaming(true);
      setStatusMessage("");
    }
  }, [cameraReady, connectionState, isStreaming]);

  // Video-style pump: snapshot from preview at TARGET_CAPTURE_FPS
  useEffect(() => {
    if (!isStreaming || connectionState !== "connected" || !cameraReady) {
      return;
    }

    let active = true;
    let captureErrors = 0;

    const pump = async () => {
      while (active && streamingRef.current) {
        const t0 = Date.now();

        try {
          const socket = socketRef.current;
          const camera = cameraRef.current;
          if (!camera || socket?.state !== "connected") {
            await sleep(50);
            continue;
          }

          const bytes = await camera.captureFrame();
          captureErrors = 0;

          if (bytes && bytes.length >= 100) {
            socket.sendFrameBytes(bytes);
            bumpFpsCounter();
          }
        } catch (err) {
          captureErrors += 1;
          if (captureErrors === 1 || captureErrors % 10 === 0) {
            const msg =
              err instanceof Error ? err.message : "Frame capture failed";
            setStatusMessage(`Capture: ${msg}`);
          }
          await sleep(150);
        }

        const elapsed = Date.now() - t0;
        const wait = FRAME_INTERVAL_MS - elapsed;
        if (wait > 0) {
          await sleep(wait);
        }
      }
    };

    void pump();

    return () => {
      active = false;
    };
  }, [isStreaming, connectionState, cameraReady, cameraRef, bumpFpsCounter]);

  return {
    serverHost,
    setServerHost,
    connectionState,
    statusMessage,
    hudUri,
    isStreaming,
    framesSent,
    captureFps,
    cameraReady,
    setCameraReady,
    connect,
    disconnect,
    startStreaming,
    stopStreaming,
  };
}
