# 🎬 SonyHub — Apple-Inspired Home Theater Control Center

**SonyHub** is a cinematic, modern home theater control center application crafted for Sony Bravia OLED displays, multi-channel AV receivers, and soundbars. Built with an Apple-inspired minimal design aesthetic, glassmorphic surfaces, fluid spring physics, and full TV remote directional navigation.

---

## 🌟 Key Highlights

- **Design Aesthetics**: Apple-inspired minimalism, deep OLED True Black (`#000000`) designed for Sony Bravia QD-OLED panels, pristine white Apple Light theme, iOS spring physics (`cubic-bezier(0.34, 1.56, 0.64, 1)`), and Lucide SF-style iconography.
- **Two Adaptive Layout Modes**:
  - 📺 **TV Mode** (> 1024px or toggle): Left 80px/96px icon sidebar, 56px+ remote-friendly touch/remote targets, high-contrast focus rings (`outline: 3px solid #0A84FF`), and full arrow key spatial D-pad navigation.
  - 📱 **iPhone Mode** (≤ 768px): Native bottom tab bar with 5 sections and full-width touch-optimized cards.
- **Zero Build Step**: Single self-contained `index.html` file powered by **Alpine.js** and **Tailwind CSS**. Works immediately when opened in any browser or TV web browser.
- **Persistent State**: Volume, active presets, 6-band EQ levels, speaker trim balances, enhancements, Spotify configuration, theme, and network settings persist via `localStorage`.

---

## 🎛 App Structure & Features

### 1. 🏠 Home (Dashboard)
- **Now Playing Hero Card**: Full-width cinematic card featuring blurred album art background, high-contrast typography, source badges, scrubable progress bar with timestamp indicators, transport controls (⏮ ⏯ ⏭), and real-time playback simulation.
- **Quick Scene Presets**:
  - 🎬 **Movie Night**: Dims to cinematic, bass boost, center dialogue lift, and Dolby Surround mode.
  - 🎵 **Music Mode**: Audiophile stereo balance, neutral EQ curve, natural room acoustics.
  - 🎮 **Gaming**: Low-latency profile, enhanced footsteps treble, and front soundstage focus.
  - ⚽ **Sports**: Clear Voice enabled, center channel boosted (+4 dB), stadium crowd EQ.
  - *Tapping any preset animates with iOS spring physics, updates the Sound EQ sliders & speaker trims, and fires an instant toast confirmation.*
- **Shortcuts Bar**: Rapid AV input switcher (`HDMI 1 (eARC)`, `HDMI 2 (PS5)`, `Bluetooth`, `Optical`) and quick master volume slider with flanking nudge buttons.

---

### 2. 🔊 Sound Control
- **Master Theater Gain**: High-fidelity amplifier control with live decibel readout (`-80 dB` to `+10 dB` reference scale).
- **Speaker Level Balance**: 5 individual channel trim sliders (`-10 dB` to `+10 dB`):
  - Front Left (`FL`)
  - Front Right (`FR`)
  - Center Channel (Dialogue clarity)
  - Surround Left & Right (`SL / SR`)
  - Subwoofer LFE Punch
- **6-Band Parametric EQ Rack**: Visual vertical EQ sliders arranged like a studio rack:
  - Bands: **Sub (60Hz)**, **Bass (200Hz)**, **Low-Mid (500Hz)**, **Mid (2kHz)**, **Hi-Mid (6kHz)**, and **Treble (16kHz)**.
  - Color-coded feedback: System blue (`#0A84FF`) when boosted, neutral gray at 0 dB, warm amber (`#FF9500`) when cut.
  - Touch/pointer drag interaction with live decibel readouts.
  - **Reset EQ** button: Returns all bands to 0 dB flat reference.
  - **Load from Audio Tuner**: Automatically detects and loads room calibration curves from the AI Room Analyzer or applies a Sony acoustic calibration profile.
- **Surround Processing**: Segmented selector for `Stereo`, `Surround`, `Dolby`, `DTS`, and `Auto`.
- **Intelligent DSP Enhancements**: iOS-style switches for `Clear Voice`, `Night Mode` (dynamic range compression), `Bass Boost`, and `Dialogue Enhancement`.

---

### 3. 🎵 Spotify Controller
- **Connection States**:
  - Connect via **OAuth 2.0 PKCE** flow (client-side SHA-256 verifier and challenge without requiring a backend server).
  - Instant **Interactive Demo Mode** to test the full music player experience immediately without setting up Spotify Developer credentials.
- **Now Playing Display**: Large high-resolution artwork, bouncing waveform animation bars, heart (favorite) button, shuffle, repeat, previous, play/pause, and next controls.
- **Recently Played**: Curated horizontal row of albums and spatial audio tracks with one-tap playback.
- **Home Theater Routing**: Stream directly to your Sony Bravia / HT-A7000 sound system.

---

### 4. 🎬 Discover (AI Recommendations)
- **Mood Selector**: Instant filter pills:
  - 😊 **Feel Good**
  - 😱 **Thriller**
  - 😂 **Comedy**
  - 💔 **Drama**
  - 🚀 **Sci-Fi**
  - 👨‍👩‍👧 **Family**
- **Dynamic Time Context**: Auto-detected from local time (`Good evening · Perfect for a movie night`, `Good morning · Light & inspiring viewing`, etc.).
- **Smart Recommendation Cards**:
  - Match score badge (e.g. `98% Match`).
  - Streaming service tags with authentic brand colors (Netflix, Prime Video, Disney+, Hulu, HBO Max).
  - **AI "Why This?" Insight**: Concise 1-sentence reasoning tailored to your room context.
  - Detailed modal drawer with plot overview, technical audio recommendation, and a **Tune Theater & Watch Now** button.
- **Dual Engine Architecture**: Connects to the local FastAPI backend at `http://localhost:8000/recommend` when running, with graceful zero-latency fallback to curated movie datasets.

---

### 5. ⚙️ Settings
- **Hardware & Network**: System display name, AV receiver IP address, and HDMI-CEC auto-detection toggle.
- **Spotify Authentication**: Configurable Client ID and redirect URI helper.
- **AI Recommendation Backend**: Configurable API endpoint with live health probe ping (`GET /health`).
- **Display Preferences**: Theme switcher (OLED True Black, Apple Light, Auto) and TV Layout Mode force toggle.
- **Keyboard & Remote Guide**: Full list of shortcut keys.

---

## 🎮 TV Remote & Keyboard Navigation

SonyHub includes a spatial directional navigation engine that calculates orthogonal distances between interactive elements, making it suitable for TV remotes and keyboards:

| Key / Input | Action |
| :--- | :--- |
| **Arrow Up / Down / Left / Right** | D-Pad spatial navigation between buttons, cards, and sliders |
| **Enter / Return** | Activate focused card, button, or switch |
| **Space** | Toggle Play / Pause |
| **M** | Toggle Mute |
| **1 – 5** | Quick switch sections (1: Home, 2: Sound, 3: Spotify, 4: Discover, 5: Settings) |
| **Escape** | Close open modals or drawers |

---

## 🚀 Getting Started

### Option 1: Direct File Open
Double click `index.html` or open it in Google Chrome, Microsoft Edge, Safari, or your Sony Bravia TV's browser.

### Option 2: Local HTTP Server
Run a lightweight HTTP server from this folder:

```bash
# Using Python
python -m http.server 3000

# Using Node / npx
npx serve .
```

Then visit `http://localhost:3000` on your computer or TV.

---

## 🔗 Ecosystem Integration

- **AI Backend**: Connects to the FastAPI backend located at `../api/` (`http://localhost:8000`). Run `uvicorn main:app --reload` to enable live Gemini AI + TMDB recommendations.
- **Room Acoustic Tuner**: Saved room measurements from `../audio-tuner/` are instantly loaded when you tap **Load from Audio Tuner** in the Sound section.

---

*SonyHub is an independent home theater interface built for Sony Bravia and multi-channel audio enthusiasts.*
