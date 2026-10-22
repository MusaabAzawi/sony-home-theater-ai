"""
config.py — Configuration loader for Sony Home Theater AI API.

Reads API keys and settings from a .env file using python-dotenv.
Raises clear, actionable errors if required keys are missing.
"""

import os
from dotenv import load_dotenv

# Load variables from .env file into the environment (no-op if file doesn't exist)
load_dotenv()


def _require_env(key: str, hint: str) -> str:
    """
    Retrieve a required environment variable or raise a descriptive RuntimeError.

    Args:
        key:  The environment variable name.
        hint: A human-readable hint on how to obtain the value.

    Returns:
        The value of the environment variable.

    Raises:
        RuntimeError: If the variable is not set or is empty.
    """
    value = os.getenv(key, "").strip()
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {key}\n"
            f"  → {hint}\n"
            f"  → Copy .env.example to .env and fill in your keys."
        )
    return value


# ---------------------------------------------------------------------------
# API Keys — required at startup
# ---------------------------------------------------------------------------

GEMINI_API_KEY: str = _require_env(
    "GEMINI_API_KEY",
    "Get a free key at https://aistudio.google.com/app/apikey",
)

TMDB_API_KEY: str = _require_env(
    "TMDB_API_KEY",
    "Get a free key at https://www.themoviedb.org/settings/api",
)

# ---------------------------------------------------------------------------
# TMDB base URLs
# ---------------------------------------------------------------------------

TMDB_BASE_URL: str = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL: str = "https://image.tmdb.org/t/p/w500"   # 500-px wide poster

# ---------------------------------------------------------------------------
# Gemini model
# ---------------------------------------------------------------------------

GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# ---------------------------------------------------------------------------
# In-memory cache settings
# ---------------------------------------------------------------------------

# How long (in seconds) a cached recommendation stays valid (default: 5 minutes)
CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))
