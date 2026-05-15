import {
  buildHealthUrl,
  buildWsUrl,
  HUD_DISPLAY_INTERVAL_MS,
  parseBackendHost,
  WS_MAX_BUFFERED_BYTES,
} from "../config";
import {
  base64ToArrayBuffer,
  canSendOnSocket,
  toSendBuffer,
} from "../utils/bytes";

export type ConnectionState = "idle" | "connecting" | "connected" | "error";

type HudFrameHandler = (uri: string) => void;
type StateHandler = (state: ConnectionState, message?: string) => void;

/**
 * WebSocket client for SkulVision backend.
 * Protocol: send JPEG bytes → receive HUD-rendered JPEG bytes.
 */
export class SkulVisionSocket {
  private ws: WebSocket | null = null;
  private onHud: HudFrameHandler | null = null;
  private onState: StateHandler | null = null;
  private _state: ConnectionState = "idle";
  private lastHudDisplayAt = 0;
  private pendingHudBase64: string | null = null;
  private hudFlushTimer: ReturnType<typeof setTimeout> | null = null;

  get state(): ConnectionState {
    return this._state;
  }

  canSendFrame(): boolean {
    const ws = this.ws;
    return ws != null && canSendOnSocket(ws, WS_MAX_BUFFERED_BYTES);
  }

  setHudHandler(handler: HudFrameHandler | null): void {
    this.onHud = handler;
  }

  setStateHandler(handler: StateHandler | null): void {
    this.onState = handler;
  }

  async connect(hostInput: string): Promise<void> {
    this.disconnect();
    this.setState("connecting");

    let parsed;
    try {
      parsed = parseBackendHost(hostInput);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Invalid host";
      this.setState("error", msg);
      return;
    }

    const { host, port } = parsed;
    const healthUrl = buildHealthUrl(hostInput);

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);
      const res = await fetch(healthUrl, { signal: controller.signal });
      clearTimeout(timeout);
      if (!res.ok) {
        this.setState("error", `Backend returned ${res.status} at ${host}:${port}`);
        return;
      }
    } catch {
      this.setState(
        "error",
        `Cannot reach http://${host}:${port}/health — same Wi-Fi? Firewall open? Backend running?`
      );
      return;
    }

    const url = buildWsUrl(hostInput);
    const ws = new WebSocket(url);
    ws.binaryType = "arraybuffer";
    this.ws = ws;

    ws.onopen = () => this.setState("connected");
    ws.onerror = () => this.setState("error", `WebSocket failed: ${url}`);
    ws.onclose = (ev) => {
      if (this._state !== "idle" && this._state !== "connected") {
        this.setState("error", ev.reason || `Closed (${url})`);
      } else if (this._state === "connected") {
        this.setState("error", "Connection lost");
      }
    };
    ws.onmessage = (event) => this.handleMessage(event.data);
  }

  disconnect(): void {
    if (this.hudFlushTimer) {
      clearTimeout(this.hudFlushTimer);
      this.hudFlushTimer = null;
    }
    if (this.ws) {
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onerror = null;
      this.ws.onclose = null;
      if (this.ws.readyState === WebSocket.OPEN) {
        this.ws.close();
      }
      this.ws = null;
    }
    this.pendingHudBase64 = null;
    this.setState("idle");
  }

  sendFrameBase64(base64: string): void {
    this.sendFrameBytes(new Uint8Array(base64ToArrayBuffer(base64)));
  }

  sendFrameBytes(bytes: Uint8Array): void {
    const ws = this.ws;
    if (!ws || !canSendOnSocket(ws, WS_MAX_BUFFERED_BYTES)) {
      return;
    }
    if (bytes.length < 100) {
      return;
    }
    ws.send(toSendBuffer(bytes));
  }

  private handleMessage(data: WebSocketMessageEvent["data"]): void {
    const deliver = (bytes: Uint8Array) => {
      if (bytes.length < 100) {
        return;
      }
      this.queueHudFrame(bytes);
    };

    if (data instanceof ArrayBuffer) {
      deliver(new Uint8Array(data));
      return;
    }

    if (typeof Blob !== "undefined" && data instanceof Blob) {
      void data.arrayBuffer().then((buf) => deliver(new Uint8Array(buf)));
    }
  }

  private queueHudFrame(bytes: Uint8Array): void {
    this.pendingHudBase64 = this.uint8ToBase64(bytes);

    const now = Date.now();
    const elapsed = now - this.lastHudDisplayAt;
    if (elapsed >= HUD_DISPLAY_INTERVAL_MS) {
      this.flushHudFrame();
      return;
    }

    if (this.hudFlushTimer) {
      return;
    }

    this.hudFlushTimer = setTimeout(() => {
      this.hudFlushTimer = null;
      this.flushHudFrame();
    }, HUD_DISPLAY_INTERVAL_MS - elapsed);
  }

  private flushHudFrame(): void {
    const base64 = this.pendingHudBase64;
    if (!base64) {
      return;
    }
    this.pendingHudBase64 = null;
    this.lastHudDisplayAt = Date.now();
    this.onHud?.(`data:image/jpeg;base64,${base64}`);
  }

  private uint8ToBase64(bytes: Uint8Array): string {
    const chunkSize = 0x8000;
    let binary = "";
    for (let i = 0; i < bytes.length; i += chunkSize) {
      const chunk = bytes.subarray(i, i + chunkSize);
      binary += String.fromCharCode(...chunk);
    }
    return btoa(binary);
  }

  private setState(state: ConnectionState, message?: string): void {
    this._state = state;
    this.onState?.(state, message);
  }
}
