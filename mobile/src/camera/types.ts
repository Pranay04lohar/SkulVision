export type HudCameraHandle = {
  /** Capture one JPEG frame from the live preview pipeline. */
  captureFrame: () => Promise<Uint8Array | null>;
};
