# 📱 SonyHub PWA Installation & Setup Guide

Welcome to **SonyHub** — your cinematic home theater control center transformed into a Progressive Web App (PWA) with native iOS fullscreen support, OLED True Black styling, and direct hardware remote control.

---

## 📲 On iPhone / iPad (Safari)

Follow these steps to install SonyHub directly onto your iOS Home Screen without the App Store:

1. 🌐 **Verify Local Server**: Make sure your Mac, PC, or Raspberry Pi is running the SonyHub local server on port 3000 (see instructions below).
2. 🧭 **Open Safari**: On your iPhone, open **Apple Safari** (must be Safari — iOS only enables PWA home screen installation via Safari).
3. 🔗 **Navigate to SonyHub**: Type `http://YOUR-HOST-IP:3000` (e.g., `http://192.168.1.100:3000`).
4. 📤 **Tap Share Button**: Tap the **Share** icon at the bottom center of Safari (the square box with an arrow pointing up).
5. ➕ **Add to Home Screen**: Scroll down the share sheet and tap **Add to Home Screen**.
6. 🏷️ **Name App**: Ensure the title is set to **SonyHub** and tap **Add** in the top-right corner.
7. ✨ **Launch**: The sleek **SonyHub** app icon will appear directly on your iOS home screen!
8. 🎬 **Native Fullscreen Experience**: Tap the icon to launch. SonyHub opens in standalone fullscreen mode without Safari URL bars or browser chrome, with translucent status bar styling.

---

## 📺 On Sony Bravia TV (Built-in Browser)

1. 🌐 **Open TV Browser**: Open the built-in Internet Browser (or Silk / Chrome) on your Sony Bravia Android / Google TV.
2. 🔗 **Enter URL**: Navigate to `http://YOUR-HOST-IP:3000`.
3. ⭐ **Bookmark / Set Homepage**: Add the page to your favorites or configure it as your browser startup page.
4. 🎮 **Remote Control Navigation**: Use the D-Pad on your Sony TV remote (Up, Down, Left, Right, Enter) to smoothly navigate all controls, presets, and audio bands.
5. ⌨️ *(Optional)* Plug in a wireless USB mini keyboard / trackpad into the Bravia USB port for effortless text searches.

---

## 🚀 Starting the Local Server

### 1. Simple Python Server (Mac, Linux, Raspberry Pi)
```bash
# Navigate to your sonyhub folder
cd sony-home-theater-ai/sonyhub

# Start HTTP server on port 3000
python3 -m http.server 3000
```

### 2. Windows PowerShell
```powershell
cd sony-home-theater-ai\sonyhub
python -m http.server 3000
```

### 3. Finding Your Local IP Address
- **macOS / Linux**: Run `ipconfig getifaddr en0` or `hostname -I`.
- **Windows**: Run `ipconfig` and look for the **IPv4 Address** (e.g. `192.168.1.100`).

---

## 🔄 Auto-Start on Mac Login (LaunchAgent)

To run the SonyHub web server continuously in the background whenever you log in to your Mac:

1. Open the included [`com.sonyhub.server.plist`](file:///C:/Users/azawi.m/.gemini/antigravity/scratch/sony-home-theater-ai/sonyhub/com.sonyhub.server.plist) file.
2. Adjust the `<key>WorkingDirectory</key>` string to match the absolute path of your `sonyhub` directory (e.g. `/Users/yourusername/Documents/sony-home-theater-ai/sonyhub`).
3. Copy the plist file into your personal LaunchAgents directory:
   ```bash
   cp com.sonyhub.server.plist ~/Library/LaunchAgents/
   ```
4. Load and start the background agent:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.sonyhub.server.plist
   ```
5. To stop or remove:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.sonyhub.server.plist
   ```

---

## 🎨 Exporting PNG Icons (`icon-192.png` & `icon-512.png`)

SonyHub comes with a master vector [`icon.svg`](file:///C:/Users/azawi.m/.gemini/antigravity/scratch/sony-home-theater-ai/sonyhub/icon.svg). To export high-resolution PNGs for iOS and Android:

1. Open [`generate_icons.html`](file:///C:/Users/azawi.m/.gemini/antigravity/scratch/sony-home-theater-ai/sonyhub/generate_icons.html) in any web browser.
2. Click **Download Both PNG Icons** (or click the 192px and 512px buttons individually).
3. Save the downloaded files (`icon-192.png` and `icon-512.png`) directly into the `sonyhub/` folder.

---

## 🎛️ Infrared (IR) Hardware Remote Integration

SonyHub includes direct integration with the local IR daemon (running by default on `http://localhost:8001`):

- **Power Toggle**: Tap the **[⏻ Power]** button in the header bar.
- **Hardware Volume**: Use **[▼ VOL]** and **[▲ VOL]** buttons in the Sound section or Quick Volume card to trigger step-by-step IR commands.
- **Configuration & Health**: Check Settings → **IR Blaster & Hardware Remote** to customize your IR server URL or inspect the live online/offline status dot.
