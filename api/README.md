# 🎬 Sony Home Theater AI — Backend API

AI-powered movie and TV show recommendations for your home theater, running on a Raspberry Pi.

---

## Architecture

```
TV Browser  →  GET /recommend?mood=action&time=night
                      ↓
              FastAPI (Raspberry Pi :8000)
                      ↓
         ┌────────────┴────────────┐
     Gemini API             TMDB API
   (pick the title)    (poster + trailer)
```

---

## 1. Prerequisites

- Raspberry Pi running Raspberry Pi OS (64-bit recommended)
- Python 3.10 or newer (`python3 --version`)
- Internet access for API calls

---

## 2. Get API Keys (both are free)

### Google Gemini API Key
1. Visit [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Click **Create API key**
3. Copy the key — you'll need it in step 4

### TMDB API Key
1. Create a free account at [https://www.themoviedb.org](https://www.themoviedb.org)
2. Go to **Settings → API → Create → Developer**
3. Fill in the form (use "Personal / Home" for type)
4. Copy the **API Key (v3 auth)** value

---

## 3. Installation

```bash
# Clone or copy this project onto your Pi
cd ~/sony-home-theater-ai/api

# Create a virtual environment (keeps deps isolated)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 4. Configuration

```bash
# Copy the example env file
cp .env.example .env

# Open it and fill in your keys
nano .env
```

Your `.env` should look like:

```
GEMINI_API_KEY=AIza...your_real_key...
TMDB_API_KEY=abc123...your_real_key...
```

Optional overrides you can add:

| Variable           | Default              | Description                          |
|--------------------|----------------------|--------------------------------------|
| `GEMINI_MODEL`     | `gemini-1.5-flash`   | Gemini model to use                  |
| `CACHE_TTL_SECONDS`| `300`                | Seconds to cache same mood+time pair |

---

## 5. Run the Server

```bash
# Make sure your venv is active
source venv/bin/activate

# Start the API server (accessible on your local network)
uvicorn main:app --host 0.0.0.0 --port 8000
```

Test it:
```bash
curl "http://localhost:8000/health"
# → {"status":"ok"}

curl "http://localhost:8000/recommend?mood=action&time=night"
# → {"title":"...", "poster_url":"...", ...}
```

The interactive API docs are available at:  
**http://\<pi-ip\>:8000/docs**

---

## 6. Auto-start on Raspberry Pi Boot (systemd)

This makes the API start automatically whenever your Pi powers on.

### 6a. Create the service file

```bash
sudo nano /etc/systemd/system/home-theater-ai.service
```

Paste this content (adjust `User` and paths to match your setup):

```ini
[Unit]
Description=Sony Home Theater AI — FastAPI backend
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/sony-home-theater-ai/api
ExecStart=/home/pi/sony-home-theater-ai/api/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5s

# Load the .env file so API keys are available
EnvironmentFile=/home/pi/sony-home-theater-ai/api/.env

[Install]
WantedBy=multi-user.target
```

### 6b. Enable and start the service

```bash
# Reload systemd to recognise the new service
sudo systemctl daemon-reload

# Enable it to start on boot
sudo systemctl enable home-theater-ai

# Start it now (without rebooting)
sudo systemctl start home-theater-ai

# Check it's running
sudo systemctl status home-theater-ai
```

### 6c. Useful commands

```bash
# View live logs
sudo journalctl -u home-theater-ai -f

# Restart after code changes
sudo systemctl restart home-theater-ai

# Stop the service
sudo systemctl stop home-theater-ai
```

---

## 7. API Reference

### `GET /health`
Liveness probe.

**Response:**
```json
{ "status": "ok" }
```

---

### `GET /recommend`

| Parameter | Type   | Required | Values                               |
|-----------|--------|----------|--------------------------------------|
| `mood`    | string | ✅       | e.g. `action`, `romantic`, `funny`, `scary`, `relaxing` |
| `time`    | string | ✅       | `morning` \| `afternoon` \| `evening` \| `night`        |

**Example:**
```
GET /recommend?mood=relaxing&time=morning
```

**Response:**
```json
{
  "title": "My Neighbor Totoro",
  "year": "1988",
  "description": "Two sisters move to the countryside and discover friendly forest spirits. A gentle, heartwarming Miyazaki classic perfect for a quiet morning.",
  "genre": "Animation / Family",
  "streaming_platform": "Netflix",
  "match_score": 94,
  "poster_url": "https://image.tmdb.org/t/p/w500/rtGDOeG9LzoerkDGZF9dnVeLppL.jpg",
  "trailer_url": "https://www.youtube.com/watch?v=92a7Hj0ijLs",
  "why_recommended": "A calming, imaginative film that pairs perfectly with a relaxed morning mood."
}
```

> **Note:** Identical `mood` + `time` combinations are cached for 5 minutes to avoid unnecessary API calls and keep response times fast.

---

## 8. Troubleshooting

| Problem | Fix |
|---|---|
| `Missing required environment variable: GEMINI_API_KEY` | Ensure `.env` file exists and has the key filled in |
| `504` or timeout from Gemini | Check Pi's internet connection; Gemini has a free tier rate limit |
| `poster_url` is `null` | TMDB couldn't find the title — the recommendation is still valid |
| Service won't start | Run `sudo journalctl -u home-theater-ai -n 50` for detailed logs |
