"""
Configuration module for Sony Home Theater IR Control Server.

Loads environment variables, manages Sony IR code mappings,
and handles overrides from learned_codes.json.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger("ir_server.config")

# Load .env file from the current directory or parent directory
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

# Server Settings
SERVER_HOST: str = os.getenv("IR_SERVER_HOST", "0.0.0.0")
SERVER_PORT: int = int(os.getenv("IR_SERVER_PORT", "8001"))

# Backend selection: auto | broadlink | lirc | gpio | mock
IR_BACKEND: str = os.getenv("IR_BACKEND", "auto").strip().lower()

# Broadlink Settings
BROADLINK_IP: Optional[str] = os.getenv("BROADLINK_IP", None)
BROADLINK_MAC: Optional[str] = os.getenv("BROADLINK_MAC", None)
BROADLINK_TIMEOUT: int = int(os.getenv("BROADLINK_TIMEOUT", "5"))

# LIRC / Raspberry Pi Settings
LIRC_REMOTE: str = os.getenv("LIRC_REMOTE", "SONY_HT")
LIRC_COMMAND: str = os.getenv("LIRC_COMMAND", "irsend")

# Learned codes storage
LEARNED_CODES_FILE: Path = BASE_DIR / "learned_codes.json"

# ==============================================================================
# SONY HOME THEATER DEFAULT IR CODES (Broadlink base64 format)
# IMPORTANT: These are placeholder codes. Use ir_learn.py to learn your actual Sony codes.
# ==============================================================================
SONY_IR_CODES: Dict[str, str] = {
    'volume_up':    'JgBGAAABK5YTERQRFBEUERQRFBEUERQRFBEAABFFERQRFBEUERQRFBEAABFFERQRFBEUERQRFBEAABFAAAAAAAAAAAAAAAAAA==',
    'volume_down':  'JgBGAAABK5YTERQRFBEUERQRFBEUERQRFBEAABFFERQRFBEUERQRFBEAABFFERQRFBEUERQRFBEAABFAAAAAAAAAAAAAAAAAA==',
    'mute':         'JgBYAAABKZUUEBQQFBAUEBQQFBAUEBQQFAABKBQQFBAUEBQQFBAUEBQQFBAUEAABJ5UUEBQQFBAUBBBQUEBQQFBQUEAAAAA==',
    'power':        'JgBYAAABKZUUEBQQFBAUEBQQFBAUEBQQFAABKBQQFBAUEBQQFBAUEBQQFBAUEAABJ5UUEBQQFBAUBBBQUEBQQFBQUEAAAAA==',
    'hdmi1':        'JgBYAAABKZUUEBQQFBAUEBQQFBAUEBQQFAABKBQQFBAUEBQQFBAUEBQQFBAUEAABJ5UUEBQQFBAUBBBQUEBQQFBQUEAAAAA==',
    'hdmi2':        'JgBYAAABKZUUEBQQFBAUEBQQFBAUEBQQFAABKBQQFBAUEBQQFBAUEBQQFBAUEAABJ5UUEBQQFBAUBBBQUEBQQFBQUEAAAAA==',
    'bluetooth':    'JgBYAAABKZUUEBQQFBAUEBQQFBAUEBQQFAABKBQQFBAUEBQQFBAUEBQQFBAUEAABJ5UUEBQQFBAUBBBQUEBQQFBQUEAAAAA==',
    'optical':      'JgBYAAABKZUUEBQQFBAUEBQQFBAUEBQQFAABKBQQFBAUEBQQFBAUEBQQFBAUEAABJ5UUEBQQFBAUBBBQUEBQQFBQUEAAAAA==',
    'movie_mode':   'JgBYAAABKZUUEBQQFBAUEBQQFBAUEBQQFAABKBQQFBAUEBQQFBAUEBQQFBAUEAABJ5UUEBQQFBAUBBBQUEBQQFBQUEAAAAA==',
    'music_mode':   'JgBYAAABKZUUEBQQFBAUEBQQFBAUEBQQFAABKBQQFBAUEBQQFBAUEBQQFBAUEAABJ5UUEBQQFBAUBBBQUEBQQFBQUEAAAAA==',
    'gaming_mode':  'JgBYAAABKZUUEBQQFBAUEBQQFBAUEBQQFAABKBQQFBAUEBQQFBAUEBQQFBAUEAABJ5UUEBQQFBAUBBBQUEBQQFBQUEAAAAA==',
    'sports_mode':  'JgBYAAABKZUUEBQQFBAUEBQQFBAUEBQQFAABKBQQFBAUEBQQFBAUEBQQFBAUEAABJ5UUEBQQFBAUBBBQUEBQQFBQUEAAAAA==',
}

# LIRC Command Name Mappings
LIRC_KEY_MAP: Dict[str, str] = {
    'volume_up':    'KEY_VOLUMEUP',
    'volume_down':  'KEY_VOLUMEDOWN',
    'mute':         'KEY_MUTE',
    'power':        'KEY_POWER',
    'hdmi1':        'KEY_FN_1',
    'hdmi2':        'KEY_FN_2',
    'bluetooth':    'KEY_BLUETOOTH',
    'optical':      'KEY_AUX',
    'movie_mode':   'KEY_MODE_MOVIE',
    'music_mode':   'KEY_MODE_MUSIC',
    'gaming_mode':  'KEY_MODE_GAME',
    'sports_mode':  'KEY_MODE_SPORTS',
}


def load_learned_codes() -> Dict[str, str]:
    """Load learned IR codes from disk if available."""
    if LEARNED_CODES_FILE.exists():
        try:
            with open(LEARNED_CODES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            logger.warning(f"Failed to read {LEARNED_CODES_FILE}: {e}")
    return {}


def save_learned_code(command_name: str, code_base64: str) -> None:
    """Save a single learned IR code to learned_codes.json."""
    codes = load_learned_codes()
    codes[command_name] = code_base64
    save_all_learned_codes(codes)


def save_all_learned_codes(codes: Dict[str, str]) -> None:
    """Save the full dictionary of learned codes to learned_codes.json."""
    try:
        with open(LEARNED_CODES_FILE, "w", encoding="utf-8") as f:
            json.dump(codes, f, indent=2, sort_keys=True)
        logger.info(f"Saved {len(codes)} learned codes to {LEARNED_CODES_FILE}")
    except Exception as e:
        logger.error(f"Failed to write to {LEARNED_CODES_FILE}: {e}")
        raise


def get_active_ir_codes() -> Dict[str, str]:
    """
    Get active IR codes, combining default placeholder codes
    with any user-learned codes from learned_codes.json taking precedence.
    """
    codes = dict(SONY_IR_CODES)
    learned = load_learned_codes()
    codes.update(learned)
    return codes
