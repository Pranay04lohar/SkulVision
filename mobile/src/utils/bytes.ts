/** Decode base64 JPEG to a tight ArrayBuffer for WebSocket binary send. */
export function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const raw = base64.replace(/^data:image\/\w+;base64,/, "");
  const binary = atob(raw);
  const len = binary.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

/** Ensure WebSocket gets exactly the JPEG bytes (RN TypedArray quirk). */
export function toSendBuffer(bytes: Uint8Array): ArrayBuffer {
  if (
    bytes.byteOffset === 0 &&
    bytes.byteLength === bytes.buffer.byteLength
  ) {
    return bytes.buffer as ArrayBuffer;
  }
  const slice = bytes.buffer.slice(
    bytes.byteOffset,
    bytes.byteOffset + bytes.byteLength
  );
  return slice as ArrayBuffer;
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * React Native often does not implement bufferedAmount; treat missing as "ok to send".
 */
export function canSendOnSocket(
  ws: WebSocket,
  maxBufferedBytes: number
): boolean {
  if (ws.readyState !== WebSocket.OPEN) {
    return false;
  }
  const buffered = ws.bufferedAmount;
  if (typeof buffered !== "number" || Number.isNaN(buffered)) {
    return true;
  }
  return buffered < maxBufferedBytes;
}
