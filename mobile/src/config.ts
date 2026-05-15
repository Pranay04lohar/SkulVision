/**
 * Backend connection settings.
 *
 * Set EXPO_PUBLIC_BACKEND_HOST in mobile/.env to your PC's LAN IP
 * (same Wi-Fi as the phone). Find it with: ipconfig (Windows) / ifconfig (Mac).
 */
export const BACKEND_PORT = 8000;

export const DEFAULT_BACKEND_HOST =
  process.env.EXPO_PUBLIC_BACKEND_HOST ?? "192.168.0.106";

/** Target send rate for the video-style snapshot pump. */
export const TARGET_CAPTURE_FPS = 12;

/** VisionCamera takeSnapshot JPEG quality (0–100). */
export const SNAPSHOT_QUALITY = 78;

/** Expo Go fallback still-photo quality (0–1). */
export const JPEG_QUALITY = 0.55;

/**
 * Skip sending when the WebSocket send buffer is large (avoids lag buildup).
 */
export const WS_MAX_BUFFERED_BYTES = 1024 * 1024;

/** Max HUD overlay refresh rate (display only; does not limit capture). */
export const HUD_DISPLAY_INTERVAL_MS = 100;

export type ParsedBackend = {
  host: string;
  port: number;
};

/**
 * Accepts: 192.168.0.5 | 192.168.0.5:8000 | http://192.168.0.5:8000 | /192.168.0.5
 */
export function parseBackendHost(input: string): ParsedBackend {
  let s = input.trim();
  s = s.replace(/^wss?:\/\//i, "");
  s = s.replace(/^https?:\/\//i, "");
  s = s.replace(/^\/+/, "");
  s = s.split("/")[0] ?? "";

  if (!s) {
    throw new Error("Enter your PC's LAN IP address (e.g. 192.168.0.5)");
  }

  let host = s;
  let port = BACKEND_PORT;

  const colonIdx = s.lastIndexOf(":");
  if (colonIdx > 0) {
    const maybePort = s.slice(colonIdx + 1);
    if (/^\d+$/.test(maybePort)) {
      port = parseInt(maybePort, 10);
      host = s.slice(0, colonIdx);
    }
  }

  if (!host || !/^[a-zA-Z0-9.\-]+$/.test(host)) {
    throw new Error(`Invalid host: "${input}"`);
  }

  return { host, port };
}

export function buildWsUrl(input: string): string {
  const { host, port } = parseBackendHost(input);
  return `ws://${host}:${port}/ws/stream`;
}

export function buildHealthUrl(input: string): string {
  const { host, port } = parseBackendHost(input);
  return `http://${host}:${port}/health`;
}
