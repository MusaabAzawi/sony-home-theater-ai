"""
main.py — FastAPI backend for Sony Home Theater AI Recommendations.

Endpoints:
  GET /health        — Liveness probe
  GET /recommend     — AI-powered movie/show recommendation

Flow for /recommend:
  1. Check in-memory TTL cache (mood + time key)
  2. Ask Google Gemini for a recommendation in structured JSON
  3. Enrich the result with TMDB poster + trailer data
  4. Return the enriched payload; fall back to curated list on any failure
"""

import json
import logging
import time
from typing import Optional

import httpx
import google.generativeai as genai
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config  # loads + validates env vars at import time

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini client
# ---------------------------------------------------------------------------

genai.configure(api_key=config.GEMINI_API_KEY)
_gemini_model = genai.GenerativeModel(config.GEMINI_MODEL)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Sony Home Theater AI",
    description="AI-powered movie & TV show recommendations for your home theater.",
    version="1.0.0",
)

# Allow all origins so the TV browser (and local dev) can freely call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory TTL cache
# Structure: { cache_key: {"expires_at": float, "data": dict} }
# ---------------------------------------------------------------------------

_cache: dict = {}


def _cache_get(key: str) -> Optional[dict]:
    """Return cached value if it exists and hasn't expired, else None."""
    entry = _cache.get(key)
    if entry and time.monotonic() < entry["expires_at"]:
        log.info("Cache HIT for key=%s", key)
        return entry["data"]
    return None


def _cache_set(key: str, data: dict) -> None:
    """Store data in the cache with a TTL expiry timestamp."""
    _cache[key] = {
        "expires_at": time.monotonic() + config.CACHE_TTL_SECONDS,
        "data": data,
    }
    log.info("Cache SET for key=%s (TTL=%ds)", key, config.CACHE_TTL_SECONDS)


# ---------------------------------------------------------------------------
# Pydantic response model
# ---------------------------------------------------------------------------

class Recommendation(BaseModel):
    title: str
    year: str
    description: str
    genre: str
    streaming_platform: str
    match_score: int
    poster_url: Optional[str] = None
    trailer_url: Optional[str] = None
    why_recommended: str


# ---------------------------------------------------------------------------
# Curated fallback list (used when both Gemini and TMDB fail)
# ---------------------------------------------------------------------------

FALLBACK_RECOMMENDATIONS: list[dict] = [
    {
        "title": "Inception",
        "year": "2010",
        "description": (
            "A thief who steals corporate secrets through dream-sharing technology "
            "is given the inverse task of planting an idea into a CEO's mind. "
            "A visually stunning mind-bender from Christopher Nolan."
        ),
        "genre": "Sci-Fi / Thriller",
        "streaming_platform": "Netflix",
        "match_score": 88,
        "poster_url": None,
        "trailer_url": None,
        "why_recommended": "A cerebral, visually spectacular film perfect for any mood.",
    },
    {
        "title": "The Grand Budapest Hotel",
        "year": "2014",
        "description": (
            "A writer encounters the owner of an aging European hotel who tells him "
            "of his adventures decades earlier. Wes Anderson's quirky, stylish masterpiece."
        ),
        "genre": "Comedy / Drama",
        "streaming_platform": "Disney+",
        "match_score": 85,
        "poster_url": None,
        "trailer_url": None,
        "why_recommended": "Light-hearted and visually delightful — great for any time of day.",
    },
    {
        "title": "Planet Earth II",
        "year": "2016",
        "description": (
            "David Attenborough narrates stunning footage of wildlife across islands, "
            "mountains, jungles, deserts, grasslands, and cities. "
            "The definitive nature documentary series."
        ),
        "genre": "Documentary",
        "streaming_platform": "BBC iPlayer / Prime Video",
        "match_score": 90,
        "poster_url": None,
        "trailer_url": None,
        "why_recommended": "Relaxing, awe-inspiring, and beautiful — fits any mood.",
    },
]

import random


def _get_fallback() -> dict:
    """Return a random entry from the curated fallback list."""
    return random.choice(FALLBACK_RECOMMENDATIONS)


# ---------------------------------------------------------------------------
# Gemini helper
# ---------------------------------------------------------------------------

GEMINI_PROMPT_TEMPLATE = """
You are a movie recommendation AI for a home theater system.
The user is in the mood for {mood} content and it's {time} time.

Recommend ONE perfect movie or TV show.
Consider the time of day (lighter content for morning, epic films for night).

Respond ONLY with valid JSON (no markdown fences, no extra text):
{{
  "title": "...",
  "year": "...",
  "description": "2-sentence description",
  "genre": "...",
  "streaming_platform": "Netflix/Prime/Disney+/Hulu/HBO Max",
  "match_score": 95,
  "why_recommended": "One sentence explaining why this fits the mood and time"
}}
""".strip()


async def _ask_gemini(mood: str, time_of_day: str) -> dict:
    """
    Call the Gemini API and parse its JSON response.

    Returns:
        A dict with keys: title, year, description, genre,
        streaming_platform, match_score, why_recommended.

    Raises:
        Exception: On network error or malformed JSON.
    """
    prompt = GEMINI_PROMPT_TEMPLATE.format(mood=mood, time=time_of_day)
    log.info("Calling Gemini (model=%s) for mood=%s time=%s", config.GEMINI_MODEL, mood, time_of_day)

    # Gemini's Python SDK is synchronous; run in thread pool to avoid blocking
    import asyncio
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None, lambda: _gemini_model.generate_content(prompt)
    )

    raw_text = response.text.strip()

    # Strip markdown code fences if Gemini wrapped the JSON anyway
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    return json.loads(raw_text)


# ---------------------------------------------------------------------------
# TMDB helpers
# ---------------------------------------------------------------------------

async def _tmdb_search(title: str) -> Optional[dict]:
    """
    Search TMDB for a movie or TV show by title.

    Returns the first result dict from TMDB, or None on failure.
    """
    url = f"{config.TMDB_BASE_URL}/search/multi"
    params = {
        "api_key": config.TMDB_API_KEY,
        "query": title,
        "include_adult": "false",
        "language": "en-US",
        "page": "1",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return results[0] if results else None


async def _tmdb_trailer(tmdb_id: int, media_type: str) -> Optional[str]:
    """
    Fetch a YouTube trailer URL from TMDB for a given movie/TV ID.

    Returns the full YouTube URL, or None if unavailable.
    """
    url = f"{config.TMDB_BASE_URL}/{media_type}/{tmdb_id}/videos"
    params = {"api_key": config.TMDB_API_KEY, "language": "en-US"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        videos = resp.json().get("results", [])

    # Prefer official trailers on YouTube
    for video in videos:
        if video.get("site") == "YouTube" and video.get("type") == "Trailer":
            return f"https://www.youtube.com/watch?v={video['key']}"

    # Fall back to any YouTube clip
    for video in videos:
        if video.get("site") == "YouTube":
            return f"https://www.youtube.com/watch?v={video['key']}"

    return None


async def _enrich_with_tmdb(gemini_data: dict) -> dict:
    """
    Add TMDB poster_url and trailer_url to the Gemini recommendation dict.

    On any TMDB error, the original dict is returned unchanged (poster/trailer = None).
    """
    title = gemini_data.get("title", "")
    enriched = {**gemini_data, "poster_url": None, "trailer_url": None}

    try:
        result = await _tmdb_search(title)
        if not result:
            log.warning("TMDB: no results for title=%s", title)
            return enriched

        media_type = result.get("media_type", "movie")  # "movie" or "tv"
        tmdb_id = result.get("id")

        # Build poster URL
        poster_path = result.get("poster_path")
        if poster_path:
            enriched["poster_url"] = f"{config.TMDB_IMAGE_BASE_URL}{poster_path}"

        # Fetch trailer
        if tmdb_id:
            enriched["trailer_url"] = await _tmdb_trailer(tmdb_id, media_type)

        log.info("TMDB enrichment done: poster=%s trailer=%s", enriched["poster_url"], enriched["trailer_url"])

    except Exception as exc:
        log.warning("TMDB enrichment failed: %s", exc)

    return enriched


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", summary="Liveness probe")
async def health():
    """Simple health check — used by systemd and monitoring tools."""
    return {"status": "ok"}


@app.get(
    "/recommend",
    response_model=Recommendation,
    summary="Get an AI-powered movie/show recommendation",
)
async def recommend(
    mood: str = Query(
        ...,
        description="User's current mood, e.g. 'action', 'romantic', 'funny', 'scary', 'relaxing'",
        min_length=1,
        max_length=100,
    ),
    time: str = Query(
        ...,
        description="Time of day: morning | afternoon | evening | night",
        pattern="^(morning|afternoon|evening|night)$",
    ),
):
    """
    Return a single AI-curated movie or TV show recommendation.

    **Workflow:**
    1. Check in-memory cache (same mood + time within 5 min → cached response)
    2. Call Google Gemini to pick the perfect title
    3. Enrich with TMDB poster image and YouTube trailer URL
    4. Fall back to a hardcoded curated list if any step fails
    """
    cache_key = f"{mood.lower().strip()}:{time}"

    # 1. Cache check
    cached = _cache_get(cache_key)
    if cached:
        return cached

    recommendation: dict

    try:
        # 2. Gemini
        gemini_data = await _ask_gemini(mood, time)

        # 3. TMDB enrichment
        recommendation = await _enrich_with_tmdb(gemini_data)

    except Exception as exc:
        log.error("Recommendation pipeline failed (%s) — using fallback", exc)
        recommendation = _get_fallback()

    # Ensure required fields are present (defensive defaults)
    recommendation.setdefault("poster_url", None)
    recommendation.setdefault("trailer_url", None)
    recommendation.setdefault("year", "N/A")

    # 4. Cache the result
    _cache_set(cache_key, recommendation)

    return recommendation
