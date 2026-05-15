import { CameraView } from "expo-camera";
import { forwardRef, useImperativeHandle, useRef } from "react";
import { StyleSheet } from "react-native";

import { JPEG_QUALITY } from "../config";
import type { HudCameraHandle } from "./types";

type Props = {
  isActive: boolean;
  onReady: () => void;
};

/** Fallback for Expo Go — still-photo capture (~3–5 FPS). */
export const ExpoHudCamera = forwardRef<HudCameraHandle, Props>(
  function ExpoHudCamera({ isActive, onReady }, ref) {
    const cameraRef = useRef<CameraView>(null);

    useImperativeHandle(
      ref,
      () => ({
        async captureFrame(): Promise<Uint8Array | null> {
          if (!isActive) {
            return null;
          }
          const camera = cameraRef.current;
          if (!camera) {
            return null;
          }

          const photo = await camera.takePictureAsync({
            quality: JPEG_QUALITY,
            skipProcessing: false,
            shutterSound: false,
            base64: true,
            exif: false,
          });

          if (photo.base64) {
            const raw = atob(photo.base64);
            const bytes = new Uint8Array(raw.length);
            for (let i = 0; i < raw.length; i++) {
              bytes[i] = raw.charCodeAt(i);
            }
            return bytes;
          }

          if (photo.uri) {
            const res = await fetch(photo.uri);
            return new Uint8Array(await res.arrayBuffer());
          }

          return null;
        },
      }),
      [isActive]
    );

    return (
      <CameraView
        ref={cameraRef}
        style={StyleSheet.absoluteFill}
        facing="back"
        onCameraReady={onReady}
      />
    );
  }
);
