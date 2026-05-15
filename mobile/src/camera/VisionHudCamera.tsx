import { File } from "expo-file-system";
import { forwardRef, useImperativeHandle, useRef } from "react";
import { Platform, StyleSheet } from "react-native";
import {
  Camera,
  useCameraDevice,
  useCameraFormat,
} from "react-native-vision-camera";

import { SNAPSHOT_QUALITY } from "../config";
import type { HudCameraHandle } from "./types";

type Props = {
  isActive: boolean;
  onReady: () => void;
};

/**
 * VisionCamera preview + takeSnapshot — reads from the video pipeline (not still photos).
 * Target ~12–15 FPS when paired with the stream pump in useHudStream.
 */
export const VisionHudCamera = forwardRef<HudCameraHandle, Props>(
  function VisionHudCamera({ isActive, onReady }, ref) {
    const cameraRef = useRef<Camera>(null);
    const device = useCameraDevice("back");
    const format = useCameraFormat(device, [
      { videoResolution: { width: 1280, height: 720 } },
      { fps: 30 },
    ]);

    useImperativeHandle(
      ref,
      () => ({
        async captureFrame(): Promise<Uint8Array | null> {
          const cam = cameraRef.current;
          if (!cam) {
            return null;
          }

          const snap = await cam.takeSnapshot({ quality: SNAPSHOT_QUALITY });
          const path = snap.path.startsWith("file://")
            ? snap.path
            : `file://${snap.path}`;
          const bytes = await new File(path).bytes();
          return bytes.length >= 100 ? bytes : null;
        },
      }),
      []
    );

    if (!device) {
      return null;
    }

    return (
      <Camera
        ref={cameraRef}
        style={StyleSheet.absoluteFill}
        device={device}
        format={format}
        isActive={isActive}
        video={Platform.OS === "ios"}
        photo={false}
        audio={false}
        enableZoomGesture={false}
        onPreviewStarted={onReady}
      />
    );
  }
);
