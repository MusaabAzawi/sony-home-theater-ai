# Sony Home Theater IR Control Server 📡

FastAPI microservice enabling infrared (IR) remote control for Sony home theater receivers, soundbars, and AV systems (HT series, STR series, etc.). Control volume, muting, power, input switching, and DSP sound presets over a REST API.

---

## 📑 Table of Contents
1. [Hardware Options](#1-hardware-options)
2. [Installation & Setup](#2-installation--setup)
3. [Learning Sony Remote IR Codes](#3-learning-sony-remote-ir-codes)
4. [Running the IR Server](#4-running-the-ir-server)
5. [Integrating with SonyHub](#5-integrating-with-sonyhub)
6. [Raspberry Pi GPIO Setup (LIRC)](#6-raspberry-pi-gpio-setup-lirc)
7. [API Reference & Examples](#7-api-reference--examples)

---

## 1. Hardware Options

### Recommended: Broadlink RM4 Pro (~$30 - $35)
- **Device**: [Broadlink RM4 Pro on Amazon](https://www.amazon.com/dp/B0872P4HXF) or [Broadlink RM4 Mini on Amazon](https://www.amazon.com/dp/B07ZSF46BX) (~$20 for IR-only).
- **Why it's recommended**:
  - Connects directly to your 2.4GHz WiFi network.
  - Controls devices line-of-sight in your living room or entertainment center.
  - Requires zero soldering or breadboards.
  - Built-in IR receiver to learn codes directly from your Sony physical remote.
  - Fully supported via the open-source `python-broadlink` library.

> [!IMPORTANT]
> **Broadlink Setup Tip**:
> When setting up the RM4 in the Broadlink mobile app, go to **Device Settings** > **Device Property** and toggle **OFF** "Lock Device". If "Lock Device" is left ON, the device will reject local LAN commands from Python SDKs.

### Alternative: Raspberry Pi GPIO IR Transmitter
- If you run SonyHub on a Raspberry Pi positioned near your entertainment center, you can use a 940nm IR transmitter LED wired to a GPIO pin with an NPN transistor and LIRC (`irsend`).

### Testing & Development: Mock Backend
- If no physical hardware is present, the server automatically starts in **Mock Mode**, logging all commands to the terminal and responding with HTTP 200. This enables full UI testing of SonyHub without needing an IR blaster connected.

---

## 2. Installation & Setup

### Prerequisites
- Python 3.9+
- Pip and virtual environment support

### Step-by-Step Installation

1. **Navigate to the directory**:
   ```bash
   cd C:\Users\azawi.m\.gemini\antigravity\scratch\sony-home-theater-ai\ir-control
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables (optional)**:
   ```bash
   cp .env.example .env
   ```
   If your network does not allow UDP broadcast discovery, specify your Broadlink device's IP in `.env`:
   ```ini
   BROADLINK_IP=192.168.1.120
   IR_BACKEND=auto
   ```

---

## 3. Learning Sony Remote IR Codes

Every Sony receiver model (e.g., HT-S350, HT-G700, STR-DH790) may have specific IR codes. A set of default placeholder codes is included, but you should learn your receiver's exact codes for maximum reliability.

Use the included `ir_learn.py` utility:

### Interactive Guided Wizard (All Buttons)
```bash
python ir_learn.py
```
This wizard will prompt you step-by-step:
```text
Target Command: VOLUME UP (Vol +)
👉 Point your Sony remote at the Broadlink and press VOLUME UP... [waiting]
Listening for IR signal | (19s remaining)...
 Captured IR code for 'volume_up'! (68 bytes)
💾 Saved 'volume_up' to learned_codes.json
```

### Learn a Single Button
```bash
python ir_learn.py --command volume_up
python ir_learn.py --command power
python ir_learn.py --command hdmi1
```

### List and Verify Codes
```bash
python ir_learn.py --list
```

### Test Send a Learned Code
```bash
python ir_learn.py --test volume_up
```

All learned codes are saved automatically to `learned_codes.json`. When the server boots, it prioritizes `learned_codes.json` over the default codes.

---

## 4. Running the IR Server

### Start the Server
```bash
python ir_server.py
```
Or run with `uvicorn` directly:
```bash
uvicorn ir_server:app --host 0.0.0.0 --port 8001 --reload
```

### Output
```text
[INFO] Starting SonyHub IR Control Server...
[INFO] Auto-detecting IR backend...
[INFO] [BroadlinkBackend] Connected to RM4 Pro at 192.168.1.120
[INFO] Active IR Backend: broadlink (connected=True)
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
```

Interactive OpenAPI documentation is available at `http://localhost:8001/docs`.

---

## 5. Integrating with SonyHub

In SonyHub's UI or backend settings, point the IR controller to this service:

```json
{
  "ir_controller_url": "http://localhost:8001"
}
```
*(If running on a separate Raspberry Pi or server on your home network, use that machine's IP, e.g. `http://192.168.1.150:8001`).*

### How SonyHub Calls the API

- **Volume Slider**: When the user drags the volume slider to `45%`, SonyHub calls:
  ```http
  POST http://localhost:8001/ir/volume/set
  Content-Type: application/json

  {"level": 45}
  ```
  The server calculates the difference from the current volume and fires the exact number of IR pulses.

- **Source Selector Buttons**: When clicking HDMI 1, HDMI 2, Bluetooth, or Optical:
  ```http
  POST http://localhost:8001/ir/source
  Content-Type: application/json

  {"source": "hdmi1"}
  ```

- **Mute / Power Buttons**:
  ```http
  POST http://localhost:8001/ir/mute
  POST http://localhost:8001/ir/power
  ```

- **DSP Mode Presets**:
  ```http
  POST http://localhost:8001/ir/preset
  Content-Type: application/json

  {"preset": "movie"}
  ```

---

## 6. Raspberry Pi GPIO Alternative Setup (LIRC)

If you are using a Raspberry Pi with an IR emitter LED on GPIO:

1. **Install LIRC**:
   ```bash
   sudo apt-get update
   sudo apt-get install lirc
   ```

2. **Configure `/boot/config.txt`**:
   Add the overlay line (assuming IR transmitter on GPIO 17):
   ```ini
   dtoverlay=gpio-ir-tx,gpio_pin=17
   ```

3. **Configure `/etc/lirc/lirc_options.conf`**:
   ```ini
   driver    = default
   device    = /dev/lirc0
   ```

4. **Add Sony Remote Config to `/etc/lirc/lircd.conf.d/sony_ht.lircd.conf`**:
   Ensure the remote name is `SONY_HT` to match `LIRC_REMOTE=SONY_HT` in `.env`.

5. **Set `.env`**:
   ```ini
   IR_BACKEND=lirc
   LIRC_REMOTE=SONY_HT
   ```

The server detects `irsend` automatically and uses `irsend SEND_ONCE SONY_HT <command>`.

---

## 7. API Reference & Examples

### Health Check
- `GET /health`
  ```bash
  curl http://localhost:8001/health
  # Response: {"status":"ok"}
  ```

### Device Status
- `GET /ir/status`
  ```bash
  curl http://localhost:8001/ir/status
  # Response: {"device":"broadlink","connected":true,"last_command":"volume_up","estimated_volume":30}
  ```

### Volume Control
- `POST /ir/volume/up`
- `POST /ir/volume/down`
- `POST /ir/volume/set`
  ```bash
  curl -X POST http://localhost:8001/ir/volume/set \
    -H "Content-Type: application/json" \
    -d '{"level": 32}'
  ```

### Mute & Power
- `POST /ir/mute`
- `POST /ir/power`

### Source Switching
- `POST /ir/source`
  ```bash
  curl -X POST http://localhost:8001/ir/source \
    -H "Content-Type: application/json" \
    -d '{"source": "optical"}'
  ```

### DSP Mode Presets
- `POST /ir/preset`
  ```bash
  curl -X POST http://localhost:8001/ir/preset \
    -H "Content-Type: application/json" \
    -d '{"preset": "gaming"}'
  ```

### Raw IR Code Sending (Advanced)
- `POST /ir/send`
  ```bash
  curl -X POST http://localhost:8001/ir/send \
    -H "Content-Type: application/json" \
    -d '{"code": "JgBGAAABK5YTERQRFBEUERQRFBEUERQRFBEAABFFERQRFBEUERQRFBEAABFFERQRFBEUERQRFBEAABFAAAAAAAAAAAAAAAAAA=="}'
  ```
