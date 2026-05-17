# SkulVision — 30-Day Prototype Roadmap

> **Goal:** From laptop-dependent prototype → always-on cloud backend + physical glasses prototype with mode-switching buttons + working HUD on phone screen.
>
> **Honest scope:** In 30 days you get a working engineering prototype, not a consumer product. Hardware will be a rigged glasses frame with an OLED display and ESP32, not finished eyewear. That is the correct goal.

---

## System Architecture After 30 Days

```
┌─────────────────────────────────────────────────────────────────┐
│                     GLASSES MODULE                              │
│  ESP32-CAM (camera + WiFi)                                      │
│  + 4 physical buttons (mode select)                             │
│  + small OLED display (OCR/translate/math result text)          │
│  + LiPo battery                                                 │
└──────────────────┬──────────────────────────────────────────────┘
                   │ WiFi (WebSocket stream or REST)
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AWS EC2 t3.micro                            │
│                     (Mumbai / ap-south-1)                       │
│  FastAPI backend                                                │
│  ├── WS  /ws/stream     → detection mode (continuous)           │
│  ├── POST /analyze/ocr  → OCR mode (single shot)                │
│  ├── POST /analyze/translate → OCR + translation                │
│  └── POST /analyze/math → OCR + equation solve                  │
└──────────────────┬──────────────────────────────────────────────┘
                   │ WiFi (result back to phone or ESP32)
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PHONE (SkulVision app)                      │
│  Vision Camera stream (detection mode)                          │
│  HUD overlay on phone screen                                    │
│  Mode UI triggered by BLE button controller                     │
└─────────────────────────────────────────────────────────────────┘
```

**Phase 1 of 30 days (Days 1–14): No hardware yet. Phone + cloud.**
**Phase 2 of 30 days (Days 15–30): Add physical ESP32 hardware.**

---

## Hardware Shopping List

> Buy immediately so it arrives before Day 15. Prices are approximate Indian market rates (Amazon India / Robu.in / Electronicscomp.in).

### About the Camera

**The ESP32-CAM already has a camera built in.** You do not need to buy a separate camera.

The AI-Thinker ESP32-CAM module includes an **OV2640 camera** (2MP, up to 1600×1200) soldered directly onto the board. It streams JPEG frames over WiFi. This is the glasses "eye."

```
What you buy:          ESP32-CAM (one board)
What it contains:      ESP32 chip + WiFi + OV2640 camera + microSD slot
What you do NOT need:  Separate camera module
```

If you want higher resolution later, the OV5640 camera (5MP) is a drop-in upgrade to the same board — but OV2640 is more than enough for Phase 1.

---

### Tier 1 — Must Buy (Core prototype)

| Component | Purpose | Where to buy | Approx cost |
|-----------|---------|--------------|-------------|
| **ESP32-CAM module** (AI-Thinker) | WiFi + **built-in OV2640 camera** — this IS the camera | Robu.in / Amazon | ₹400–600 |
| **FTDI USB-to-TTL programmer** (CP2102 or CH340) | Flash code to ESP32-CAM — it has no USB port of its own | Robu.in / Amazon | ₹150–250 |
| **1.3" OLED I2C display** (SH1106 or SSD1306, 128×64) | Show result text on glasses | Robu.in / Amazon | ₹200–350 |
| **4x tactile push buttons** (6mm or 12mm) | Mode selection: 1=detect, 2=OCR, 3=translate, 4=math | Any electronics shop | ₹20–50 |
| **3.7V 1000mAh LiPo battery** | Power the glasses module wirelessly | Robu.in | ₹150–250 |
| **TP4056 charging module** (with protection circuit — get the one with 4 pins OUT, not 2) | Safely charge LiPo via micro-USB | Robu.in | ₹30–60 |
| **MT3608 boost converter** | Step up 3.7V battery → 5V for ESP32-CAM | Robu.in | ₹30–50 |
| **Cheap glasses frame** (lens-less, or pop out the lenses) | Mounting base for everything | Pharmacy / Amazon | ₹100–200 |
| **Dupont jumper wires** (male-to-female and male-to-male pack) | Connect components on breadboard | Any electronics shop | ₹80–120 |
| **Half-size breadboard** | Prototyping before soldering | Any electronics shop | ₹60–100 |
| **Small perfboard** (5cm × 7cm) | Permanent wiring after breadboard phase | Robu.in | ₹30–50 |
| **Soldering iron + solder wire** | Permanent connections | Amazon / local shop | ₹300–500 (if you don't have one) |
| **Hot glue gun** | Mount everything to glasses frame | Amazon | ₹150–250 |

**Total Tier 1: ~₹1600–2500 (~$20–30)**

### Tier 2 — Nice to Have

| Component | Purpose | Cost |
|-----------|---------|------|
| **ESP32-S3 DevKit** | More powerful, native USB, better BLE — upgrade path for Phase 2 | ₹800–1200 |
| **OV5640 5MP camera** | Higher resolution than built-in OV2640 — swap into same ESP32-CAM board | ₹500–700 |
| **Multimeter** | Test voltage, continuity — essential debugging tool if you don't have one | ₹300–600 |

---

## Hardware Learning Resources

> You have never worked with hardware before. Watch these **in this exact order** before touching any component. Each video is specifically matched to what you will build.

### Step 0 — Arduino IDE Setup (do this first, Day 15)

**📺 Video:** [Install the ESP32 Board in Arduino IDE in less than 1 minute](https://www.youtube.com/watch?v=mBaS3YnqDaU)
*(Rui Santos / Random Nerd Tutorials — 832K views, most trusted ESP32 resource)*

What you learn: Install Arduino IDE, add ESP32 board support URL, install ESP32 package. This is the software tool you use to write and upload code to the ESP32-CAM.

---

### Step 1 — Understanding ESP32-CAM + Flashing with FTDI (Day 16)

**📺 Video:** [ESP32 CAM — 10 Dollar Camera for IoT Projects](https://www.youtube.com/watch?v=visj0KE5VtY)
*(DroneBot Workshop — 29 min, covers FTDI wiring at 8:18, brownout fix, camera test)*

What you learn:
- What the ESP32-CAM board looks like and which pins do what
- How to wire the FTDI programmer to flash it (no USB port on this board)
- How to run the built-in camera web server example to test the camera works
- Common problems and how to fix them (brownout, failed uploads)

**Critical wiring for flashing (from this video):**
```
FTDI GND  → ESP32-CAM GND
FTDI VCC  → ESP32-CAM 5V
FTDI TX   → ESP32-CAM UOR (GPIO3)
FTDI RX   → ESP32-CAM UOT (GPIO1)
GPIO0     → GND   ← this puts it in flash mode, remove after flashing
```

---

### Step 2 — OLED Display with ESP32 (Day 19)

**📺 Video:** [How To Use The I2C 128×64 OLED Display On The ESP32](https://www.youtube.com/watch?v=_ozCI1wWyio)
*(36 min — covers wiring, library install, printing text, scrolling)*

What you learn:
- Wire SDA/SCL pins from OLED to ESP32
- Install `Adafruit_SSD1306` and `Adafruit_GFX` libraries
- Display text, control font size, clear screen
- This is how OCR / translation results will appear on the glasses

**Wiring (standard ESP32 — adjust pins for ESP32-CAM):**
```
OLED GND → GND
OLED VCC → 3.3V
OLED SCL → GPIO 22 (or 14 on ESP32-CAM)
OLED SDA → GPIO 21 (or 15 on ESP32-CAM)
```

---

### Step 3 — Push Buttons with ESP32 (Day 19)

**📺 Video:** [ESP32 Tutorial 9 — Using Push Button to Toggle LED](https://www.youtube.com/watch?v=_tLesIbpB8U)
*(SunFounder — covers button wiring, INPUT_PULLUP, debounce)*

What you learn:
- Wire a button to a GPIO pin (no external resistor needed with INPUT_PULLUP)
- Read button state in code
- Debounce (why a single press sometimes reads as 5 presses and how to fix it)

For SkulVision you need 4 buttons, each on its own GPIO pin. Same wiring × 4.

```
Button one leg → GPIO pin (e.g. 13)
Button other leg → GND
Code: pinMode(13, INPUT_PULLUP);
```

---

### Step 4 — LiPo Battery + TP4056 (Day 22)

**📺 Video:** [Power Your Projects With a Built-In Lithium Battery and a TP4056 Charger](https://www.youtube.com/watch?v=8rBnJ83STBA)
*(Ruben Lopez — practical setup, shows exactly how to wire TP4056 output to a project)*

What you learn:
- Difference between TP4056 with and without protection (always buy **with protection** — 4 output pads version)
- How to connect LiPo to TP4056
- How to safely power ESP32 from TP4056 output via boost converter
- How to charge while running (pass-through charging)

**Power circuit for SkulVision glasses:**
```
LiPo B+ / B- → TP4056 battery pads
TP4056 OUT+ / OUT- → MT3608 boost converter IN
MT3608 OUT (set to 5V) → ESP32-CAM 5V pin
ESP32-CAM 3.3V pin → OLED VCC
```

> ⚠️ **Never connect LiPo directly to ESP32 without protection circuit.** Always use TP4056 with the protection version.

---

### Step 5 — ESP32-CAM Sending Data over WiFi (Day 18, most important)

**📺 Reference (read, not video):** [Random Nerd Tutorials — ESP32-CAM WebSocket](https://randomnerdtutorials.com/esp32-cam-video-streaming-face-recognition-arduino-ide/)

Then look at: [GitHub — ESP32CamAI WebSocket client example](https://github.com/longpth/ESP32CamAI/blob/main/ESP32CamAI_arduino/ESP32CamAI_arduino.ino)

What you learn:
- Capture a JPEG frame from the camera in code: `camera_fb_t* fb = esp_camera_fb_get();`
- Send binary data over WebSocket using `arduinoWebSockets` library: `webSocket.sendBIN(fb->buf, fb->len)`
- Release frame buffer: `esp_camera_fb_return(fb);`

This is the core loop for detection mode — capture → send over WiFi → release → repeat.

---

### Beginner Mistakes to Avoid

| Mistake | What happens | Fix |
|---------|-------------|-----|
| Powering ESP32-CAM from 3.3V | Brownout, random resets | Always use 5V for ESP32-CAM |
| TP4056 without protection circuit | LiPo over-discharged → swollen/dead battery | Buy the 4-pad version with protection |
| GPIO0 left connected to GND after flashing | ESP32-CAM stuck in flash mode, won't run your code | Remove GPIO0-GND wire after flashing |
| I2C OLED address mismatch | Display shows nothing | Run I2C scanner sketch first to find address (0x3C or 0x3D) |
| Long JPEG interval sending | Camera frame buffer fills up, memory crash | Always call `esp_camera_fb_return(fb)` after every capture |
| Soldering components before testing | Hard to debug hardware problems | Always test on breadboard first, solder only when working |

---

## Week-by-Week Roadmap

---

### WEEK 1 (Days 1–7) — Deploy Backend to EC2

**Goal:** Laptop completely off. Phone connects to AWS. Everything works as before.

#### Day 1 — Launch EC2

1. AWS Console → EC2 → Launch Instance
   - **Region:** `ap-south-1` (Mumbai) — closest to India, lowest latency
   - **AMI:** Ubuntu 24.04 LTS (free tier eligible)
   - **Instance:** `t3.micro` (free tier)
   - **Storage:** 20 GB gp3
2. Security Group — open these ports:
   ```
   22   (SSH)        → Your IP only
   8000 (FastAPI)    → 0.0.0.0/0 (for phone + ESP32)
   80   (HTTP)       → 0.0.0.0/0 (later for HTTPS redirect)
   443  (HTTPS/WSS)  → 0.0.0.0/0 (for WSS)
   ```
3. Allocate and attach an **Elastic IP** (free when instance is running)

#### Day 2 — Server Setup

```bash
# SSH in
ssh -i your-key.pem ubuntu@<your-elastic-ip>

# Install dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv git nginx certbot python3-certbot-nginx -y
sudo apt install libgl1 libglib2.0-0 -y   # OpenCV deps

# Clone repo
git clone https://github.com/your/SkulVision.git
cd SkulVision
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### Day 3 — Configure and test

```bash
# Copy .env
cp .env.example .env
nano .env   # Set DEVICE=cpu, adjust settings

# Download model
python scripts/download_models.py

# Test run
python main.py
# From another terminal: curl http://localhost:8000/health
```

#### Day 4 — Systemd service (auto-start on reboot)

Create `/etc/systemd/system/skulvision.service`:
```ini
[Unit]
Description=SkulVision Backend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/SkulVision
ExecStart=/home/ubuntu/SkulVision/.venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable skulvision
sudo systemctl start skulvision
sudo systemctl status skulvision
```

#### Day 5 — HTTPS + WSS (required for mobile on real network)

```bash
# Point a domain at your Elastic IP (use free subdomain from afraid.org or get a cheap domain)
# Then:
sudo certbot --nginx -d yourdomain.com
```

Nginx config (`/etc/nginx/sites-available/skulvision`):
```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

#### Day 6 — Update mobile app

```bash
# mobile/.env
EXPO_PUBLIC_BACKEND_HOST=yourdomain.com  # or Elastic IP temporarily
```

In `mobile/src/config.ts` — update `buildWsUrl` to use `wss://` when host has a domain:
```ts
export function buildWsUrl(input: string): string {
  const { host, port } = parseBackendHost(input);
  const isIp = /^\d+\.\d+\.\d+\.\d+$/.test(host);
  const scheme = isIp ? "ws" : "wss";
  const portPart = isIp ? `:${port}` : "";
  return `${scheme}://${host}${portPart}/ws/stream`;
}
```

#### Day 7 — Validate end-to-end

Checklist:
- [ ] `curl https://yourdomain.com/health` returns OK
- [ ] Phone connects over 4G (not just Wi-Fi) — real network test
- [ ] Detection mode works, HUD visible
- [ ] `sudo systemctl status skulvision` shows active after VM reboot

---

### WEEK 2 (Days 8–14) — Mode Routing API + Mobile UI

**Goal:** 4 modes working end-to-end over EC2. Phone UI has mode buttons.

#### Day 8–9 — Backend: Mode routing endpoints

New file: `backend/api/analyze.py`

```python
POST /analyze/ocr          # Send JPEG → get OCR text back
POST /analyze/translate    # Send JPEG + target_lang → OCR + translate
POST /analyze/math         # Send JPEG → OCR equation → solve → result
```

Each endpoint:
1. Accepts multipart JPEG or base64 body
2. Runs the relevant pipeline module
3. Returns **JSON** (not a rendered JPEG) — phone draws the overlay itself

Example response from `/analyze/ocr`:
```json
{
  "mode": "ocr",
  "text": ["Hello World", "Price: ₹499"],
  "regions": [{"text": "Hello World", "confidence": 0.94, "bbox": [x,y,w,h]}],
  "processing_ms": 210
}
```

#### Day 10 — Backend: Translation module

`backend/translation/engine.py`:
- Call **AWS Translate** (boto3) — already in AWS, same account, tiny cost
- Or **LibreTranslate** self-hosted (free, private, runs on same EC2)
- Input: OCR text string + target language code
- Output: translated string

```python
import boto3
translate = boto3.client('translate', region_name='ap-south-1')
result = translate.translate_text(Text=text, SourceLanguageCode='auto', TargetLanguageCode='hi')
```

#### Day 11 — Backend: Math solver module

`backend/math/solver.py`:
- OCR the equation from the frame
- Parse with **SymPy** (free, runs locally) for algebraic/calculus
- Fallback to **Wolfram Alpha free API** for complex expressions

```python
import sympy
from sympy.parsing.sympy_parser import parse_expr
result = sympy.solve(parse_expr(equation_text))
```

**Honest note:** Printed equations work well. Handwritten math is unreliable with EasyOCR — set expectations accordingly.

#### Day 12–13 — Mobile: Mode UI

Update `ConnectionBar.tsx` to show mode buttons when connected:

```
[ DETECT ] [ OCR ] [ TRANSLATE ] [ MATH ]
```

- **DETECT**: starts WebSocket stream (existing)
- **OCR / TRANSLATE / MATH**: captures single frame → `POST /analyze/<mode>` → shows text result overlay

New `src/services/analyzeService.ts`:
```ts
export async function analyzeFrame(
  base64: string,
  mode: "ocr" | "translate" | "math",
  host: string
): Promise<AnalyzeResult>
```

New `src/components/ResultOverlay.tsx`:
- Shows text result cards on screen for 4 seconds after each single-shot analysis

#### Day 14 — Integration test

Checklist:
- [ ] Detection mode: boxes + labels over EC2
- [ ] OCR mode: tap button, text extracted and shown
- [ ] Translate mode: tap button, text translated (test with Hindi signboard photo)
- [ ] Math mode: tap button, printed equation solved
- [ ] All modes work on 4G (no local Wi-Fi)

---

### WEEK 3 (Days 15–21) — Hardware Setup

**Goal:** ESP32-CAM flashed and streaming. Physical buttons wired.

#### Day 15 — Hardware arrives + inventory check

Unbox and verify:
- [ ] ESP32-CAM module
- [ ] FTDI programmer
- [ ] 1.3" OLED display
- [ ] 4x buttons
- [ ] LiPo + TP4056 + boost converter
- [ ] Glasses frame

#### Day 16–17 — Flash ESP32-CAM

1. Install **Arduino IDE** + ESP32 board support
2. Wire FTDI to ESP32-CAM for flashing:
   ```
   FTDI GND  → ESP32-CAM GND
   FTDI VCC  → ESP32-CAM 5V
   FTDI TX   → ESP32-CAM U0R (GPIO3)
   FTDI RX   → ESP32-CAM U0T (GPIO1)
   IO0       → GND (puts it in flash mode)
   ```
3. Flash `esp32-cam-webserver` sketch first — just to test camera works
4. Then flash custom SkulVision firmware (see Day 18)

#### Day 18–19 — ESP32 firmware

`firmware/skulvision_esp32/skulvision_esp32.ino`:

```cpp
// What it does:
// 1. Connects to WiFi
// 2. Reads button state (4 buttons on GPIO pins)
// 3. In DETECT mode: streams JPEG frames to backend WebSocket
// 4. In OCR/TRANSLATE/MATH mode: captures single JPEG → HTTP POST to backend
// 5. Receives result text → displays on OLED

#include <WiFi.h>
#include <WebSocketsClient.h>
#include <Wire.h>
#include <Adafruit_SSD1306.h>

// Pins
#define BTN_DETECT    13
#define BTN_OCR       12
#define BTN_TRANSLATE 14
#define BTN_MATH      2

// Display
Adafruit_SSD1306 display(128, 64, &Wire, -1);
```

Mode logic:
```
Button 1 held → stream continuously to /ws/stream
Button 2 tap  → capture 1 frame → POST /analyze/ocr → show text on OLED
Button 3 tap  → capture 1 frame → POST /analyze/translate → show on OLED
Button 4 tap  → capture 1 frame → POST /analyze/math → show on OLED
```

Display the result on OLED as scrolling text (big enough to read through glasses).

#### Day 20–21 — OLED display test

- Wire OLED to ESP32-CAM:
  ```
  OLED SDA → GPIO 14
  OLED SCL → GPIO 15
  OLED VCC → 3.3V
  OLED GND → GND
  ```
- Test: button press → "Connecting..." → result appears on OLED
- Font size: use `u8g2` or `Adafruit_GFX` at font size 2 for readability

---

### WEEK 4 (Days 22–30) — Integration + Glasses Assembly

**Goal:** Everything mounted on glasses frame. Working demo you can wear.

#### Day 22–23 — Power system

Wire power circuit:
```
LiPo battery
    ↓
TP4056 (charge management)
    ↓
MT3608 boost converter (3.7V → 5V)
    ↓
ESP32-CAM 5V pin
    ↓ (3.3V from ESP32)
OLED display
```

Test:
- Run on battery only (no USB)
- Measure runtime: should be ~2–4 hours at full camera streaming

#### Day 24–25 — Glasses assembly

1. Remove lenses from cheap glasses frame (or use frame without lenses)
2. Mount ESP32-CAM at **top-center of frame** pointing forward
3. Mount OLED display on **right temple arm** or inner-right frame edge
4. Mount 4 buttons on **right temple arm** (reachable by right hand)
5. Route TP4056 + boost converter + LiPo behind the right ear
6. Use hot glue for initial prototype (epoxy later for permanence)

```
[LEFT]  ----[FRAME]---- [RIGHT]
              |               |
         ESP32-CAM         OLED display
         (forehead area)  (inner right)
                            |
                          [4 buttons on arm]
                            |
                          [battery + circuits behind ear]
```

#### Day 26–27 — Integration test (glasses + EC2)

Checklist:
- [ ] Wear glasses → ESP32-CAM connects to WiFi automatically
- [ ] Button 1: detection boxes visible on phone screen (phone mirrors HUD)
- [ ] Button 2: OCR text appears on OLED within 2–3 seconds
- [ ] Button 3: translation result on OLED
- [ ] Button 4: math result on OLED (test with printed equation)
- [ ] End-to-end on 4G (phone as hotspot for ESP32 or both on home WiFi)

#### Day 28 — Bug fixes + reliability

- Reconnect logic: if WiFi drops → auto-reconnect every 5 seconds
- Button debounce: minimum 300ms between button triggers
- OLED timeout: result disappears after 6 seconds, returns to idle screen showing WiFi + battery level
- Backend error handling: show "Error" on OLED if backend returns non-200

#### Day 29 — Demo preparation

- Charge glasses fully
- Test 3 scenarios:
  1. Walk past object → Button 1 → "person 0.87", "bottle 0.72" visible
  2. Point at printed text → Button 2 → OCR result on OLED
  3. Point at signboard in Hindi/other language → Button 3 → English translation on OLED
- Record screen + OLED result for documentation

#### Day 30 — Documentation + review

- Update `README.md` with hardware section
- Update `reference.md` with current state
- Note what works, what is rough, what needs Phase 2

---

## Software Checklist Summary

```
Week 1 — EC2 Deploy
[ ] EC2 t3.micro running in ap-south-1
[ ] systemd service auto-restarts backend
[ ] Nginx + HTTPS + WSS configured
[ ] Mobile app pointing to EC2

Week 2 — Mode APIs
[ ] POST /analyze/ocr working
[ ] POST /analyze/translate working (AWS Translate or LibreTranslate)
[ ] POST /analyze/math working (SymPy)
[ ] Mobile: 4 mode buttons in UI
[ ] Mobile: ResultOverlay shows text on screen

Week 3 — Hardware
[ ] ESP32-CAM flashed and streaming to EC2
[ ] Buttons wired and reading correctly
[ ] OLED showing text results
[ ] Battery power circuit working

Week 4 — Integration
[ ] Full glasses module assembled on frame
[ ] All 4 modes work end-to-end
[ ] Works on battery (no USB)
[ ] Works on 4G (no laptop, no home WiFi required)
```

---

## Honest Limitations of This 30-Day Build

| Thing | Reality |
|-------|---------|
| **Form factor** | Rigged, obviously prototype — not wearable in public |
| **Display** | OLED shows text only, not graphical bounding boxes |
| **Detection mode on glasses** | Phone still needed as secondary display for visual HUD |
| **Handwritten math** | Likely won't work reliably — printed equations only |
| **Latency over 4G** | ~200–500ms per single-shot request (acceptable for OCR/translate/math) |
| **Battery life** | ~2–4 hours streaming; longer in single-shot modes |
| **t3.micro** | Fine for personal use; add more RAM/CPU if EasyOCR is too slow |

---

## Cost Estimate

| Item | Cost |
|------|------|
| Hardware (Tier 1) | ₹1500–2000 |
| AWS EC2 t3.micro | Free (12 months free tier) |
| AWS Translate | ~$0.01/1000 chars (near-free for personal use) |
| Domain name (optional) | ₹600–1000/year |
| **Total** | **~₹2500–4000 (~$30–50)** |

---

## After 30 Days — What Comes Next

```
Phase 2 (Month 2–3)
├── Move object detection on-device (YOLOv8n TFLite in React Native)
├── Better glasses display (waveguide or projector module)
├── Voice mode (push button 4 long → Whisper transcription → LLM answer)
├── Scene understanding (describe what you're looking at)
└── BLE mode: decouple ESP32 from WiFi, route through phone

Phase 3 (Month 4–6)
├── Custom PCB (replace breadboard/perfboard)
├── Smaller form factor
├── On-device inference for all real-time modes
└── WebRTC instead of WebSocket for lower latency
```

---

> **Core principle from reference.md:** *"Build the nervous system first. The intelligence layer comes later."*
>
> After 30 days you have a nervous system that works on real hardware. Intelligence (better models, more features, better hardware) layers on top of a proven foundation.
