import { CameraView } from "expo-camera";
import { useCallback, useEffect, useRef, useState } from "react";

import { JPEG_QUALITY, MIN_CAPTURE_GAP_MS } from "../config";
import { ConnectionState, SkulVisionSocket } from "../services/skulVisionSocket";
import { sleep } from "../utils/bytes";

export function useHudStream(cameraReady: boolean) {
  const cameraRef = useRef<CameraView>(null);
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

  // Auto-start after Connect → Start HUD if camera was still initializing
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
          const camera = cameraRef.current;
          const socket = socketRef.current;
          if (!camera) {
            await sleep(100);
            continue;
          }
          if (socket?.state !== "connected") {
            await sleep(100);
            continue;
          }

          const photo = await camera.takePictureAsync({
            quality: JPEG_QUALITY,
            skipProcessing: false,
            shutterSound: false,
            base64: true,
            exif: false,
          });

          captureErrors = 0;

          if (photo?.base64) {
            socket.sendFrameBase64(photo.base64);
            bumpFpsCounter();
          } else if (photo?.uri) {
            // Fallback: some devices omit base64 even when requested
            const res = await fetch(photo.uri);
            const buf = await res.arrayBuffer();
            socket.sendFrameBytes(new Uint8Array(buf));
            bumpFpsCounter();
          }
        } catch (err) {
          captureErrors += 1;
          if (captureErrors === 1 || captureErrors % 10 === 0) {
            const msg =
              err instanceof Error ? err.message : "Camera capture failed";
            setStatusMessage(`Capture: ${msg}`);
          }
          await sleep(200);
        }

        const elapsed = Date.now() - t0;
        if (elapsed < MIN_CAPTURE_GAP_MS) {
          await sleep(MIN_CAPTURE_GAP_MS - elapsed);
        }
      }
    };

    void pump();

    return () => {
      active = false;
    };
  }, [isStreaming, connectionState, cameraReady, bumpFpsCounter]);

  return {
    cameraRef,
    serverHost,
    setServerHost,
    connectionState,
    statusMessage,
    hudUri,
    isStreaming,
    framesSent,
    captureFps,
    connect,
    disconnect,
    startStreaming,
    stopStreaming,
  };
}
