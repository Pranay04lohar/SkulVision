# SkulVision Mobile (Expo)

Phone camera → WebSocket → Python backend → HUD overlay on screen.

## Prerequisites

- Node.js 18+
- [Expo Go](https://expo.dev/go) on your phone (same Wi-Fi as dev PC)
- SkulVision backend running: `python main.py` from repo root

## Setup

```bash
cd mobile
npm install
cp .env.example .env
# Edit .env — set EXPO_PUBLIC_BACKEND_HOST to your PC's LAN IP
```

Find your PC IP:

- Windows: `ipconfig` → IPv4 Address
- Mac/Linux: `ifconfig` or `ip addr`

## Run

```bash
# Terminal 1 (repo root)
python main.py

# Terminal 2
cd mobile
npx expo start
```

Scan the QR code with Expo Go (Android) or Camera app (iOS).

## Usage

1. Enter your PC's LAN IP if not set in `.env`
2. **Connect** — opens `ws://<ip>:8000/ws/stream`
3. **Start HUD** — sends camera JPEGs, displays annotated frames from server

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Connection failed | Same Wi-Fi; Windows firewall allows port 8000 |
| Black HUD | Backend running; check `http://<ip>:8000/health` in phone browser |
| Low FPS | Normal on CPU backend; reduce send rate in `src/config.ts` |
| Android ws:// blocked | `usesCleartextTraffic` is set in `app.json` |

## Protocol

Matches `scripts/test_camera.py`:

- **Client → server:** raw JPEG bytes
- **Server → client:** HUD-rendered JPEG bytes
