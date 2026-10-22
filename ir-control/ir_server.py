"""
FastAPI IR Control Server for Sony Home Theater Hub.

Provides REST API endpoints to control Sony home theater receivers via:
  1. Broadlink RM4 Pro (WiFi IR blaster)
  2. Raspberry Pi GPIO (LIRC)
  3. Mock backend (for testing without hardware)
"""

import asyncio
import base64
import logging
import shutil
import subprocess
from contextlib import asynccontextmanager
from typing import Optional, Literal, Dict, Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("ir_server")

# Try importing broadlink
try:
    import broadlink
    BROADLINK_AVAILABLE = True
except ImportError:
    broadlink = None
    BROADLINK_AVAILABLE = False
    logger.info("broadlink library not installed. Broadlink backend will be unavailable.")


# ==============================================================================
# Backend Implementations
# ==============================================================================

class BaseIRBackend:
    """Abstract base class for IR backends."""
    name: str = "base"
    connected: bool = False
    last_command: str = "none"

    async def initialize(self) -> bool:
        """Initialize and connect to the hardware device."""
        raise NotImplementedError

    async def send_command(self, command_name: str) -> bool:
        """Send a named command (e.g. 'volume_up', 'power')."""
        raise NotImplementedError

    async def send_raw(self, code_str: str) -> bool:
        """Send a raw IR packet string (hex or base64)."""
        raise NotImplementedError

    def get_status(self) -> Dict[str, Any]:
        """Return backend status."""
        return {
            "device": self.name,
            "connected": self.connected,
            "last_command": self.last_command
        }


class MockBackend(BaseIRBackend):
    """
    Mock IR backend for local development and testing without physical hardware.
    Logs all commands to stdout.
    """
    def __init__(self):
        self.name = "mock"
        self.connected = True
        self.last_command = "none"

    async def initialize(self) -> bool:
        logger.info("[MockBackend] Initialized mock IR backend.")
        self.connected = True
        return True

    async def send_command(self, command_name: str) -> bool:
        codes = config.get_active_ir_codes()
        code = codes.get(command_name, "NO_CODE_MAPPED")
        self.last_command = command_name
        logger.info(f"[MockBackend] IR Command Sent: '{command_name}' -> [Payload: {code[:30]}...]")
        return True

    async def send_raw(self, code_str: str) -> bool:
        self.last_command = f"raw:{code_str[:12]}..."
        logger.info(f"[MockBackend] Raw IR Sent -> [Payload: {code_str[:30]}...]")
        return True


class BroadlinkBackend(BaseIRBackend):
    """
    Broadlink RM4 Pro WiFi IR blaster backend.
    Auto-discovers devices on the local network or connects via BROADLINK_IP.
    """
    def __init__(self):
        self.name = "broadlink"
        self.connected = False
        self.device = None
        self.last_command = "none"

    async def initialize(self) -> bool:
        if not BROADLINK_AVAILABLE:
            logger.warning("[BroadlinkBackend] 'broadlink' package is not installed.")
            self.connected = False
            return False

        # Run discovery / connection in a background thread to avoid blocking FastAPI
        loop = asyncio.get_running_loop()
        try:
            device = await loop.run_in_executor(None, self._connect_device)
            if device:
                self.device = device
                self.connected = True
                dev_model = getattr(self.device, "model", "Broadlink Device")
                dev_host = getattr(self.device, "host", ("Unknown", 0))[0]
                logger.info(f"[BroadlinkBackend] Connected to {dev_model} at {dev_host}")
                return True
            else:
                logger.warning("[BroadlinkBackend] No Broadlink device found.")
                self.connected = False
                return False
        except Exception as e:
            logger.error(f"[BroadlinkBackend] Error during initialization: {e}")
            self.connected = False
            return False

    def _connect_device(self):
        """Synchronous discovery/connection logic."""
        # 1. Direct IP connection if specified
        if config.BROADLINK_IP:
            logger.info(f"[BroadlinkBackend] Attempting direct connection to {config.BROADLINK_IP}...")
            try:
                # broadlink.hello() discovers device at specific IP
                if hasattr(broadlink, "hello"):
                    dev = broadlink.hello(config.BROADLINK_IP)
                    if dev:
                        dev.auth()
                        return dev
            except Exception as e:
                logger.debug(f"[BroadlinkBackend] broadlink.hello failed: {e}")

        # 2. LAN Discovery
        logger.info(f"[BroadlinkBackend] Auto-discovering Broadlink devices (timeout={config.BROADLINK_TIMEOUT}s)...")
        devices = broadlink.discover(timeout=config.BROADLINK_TIMEOUT)
        if devices:
            # Filter for RM series / IR capable if possible
            for dev in devices:
                try:
                    dev.auth()
                    logger.info(f"[BroadlinkBackend] Successfully authenticated device: {dev}")
                    return dev
                except Exception as e:
                    logger.warning(f"[BroadlinkBackend] Failed to authenticate device {dev}: {e}")
            # Fallback to first device
            dev = devices[0]
            dev.auth()
            return dev
        return None

    def _prepare_payload(self, code_str: str) -> bytes:
        """Converts base64 or hex string into raw IR bytes."""
        code_str = code_str.strip()
        try:
            # Try base64 decoding first
            return base64.b64decode(code_str)
        except Exception:
            # Fall back to hex decoding
            return bytes.fromhex(code_str.replace(" ", "").replace("0x", ""))

    async def send_command(self, command_name: str) -> bool:
        codes = config.get_active_ir_codes()
        if command_name not in codes:
            raise ValueError(f"Unknown IR command '{command_name}'.")

        code_str = codes[command_name]
        return await self.send_raw(code_str, command_label=command_name)

    async def send_raw(self, code_str: str, command_label: Optional[str] = None) -> bool:
        if not self.connected or not self.device:
            # Try to re-connect
            success = await self.initialize()
            if not success:
                raise ConnectionError("Broadlink device not connected.")

        raw_bytes = self._prepare_payload(code_str)
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self.device.send_data, raw_bytes)
            self.last_command = command_label or f"raw:{code_str[:12]}..."
            logger.info(f"[BroadlinkBackend] Sent: {self.last_command}")
            return True
        except Exception as e:
            logger.error(f"[BroadlinkBackend] Failed to send IR data: {e}")
            self.connected = False
            raise


class LircBackend(BaseIRBackend):
    """
    Raspberry Pi GPIO IR backend using LIRC ('irsend').
    """
    def __init__(self):
        self.name = "gpio"
        self.connected = False
        self.last_command = "none"

    async def initialize(self) -> bool:
        # Check if irsend command exists in system PATH
        irsend_bin = shutil.which(config.LIRC_COMMAND)
        if irsend_bin:
            self.connected = True
            logger.info(f"[LircBackend] Found LIRC binary: {irsend_bin}")
            return True
        logger.warning(f"[LircBackend] Command '{config.LIRC_COMMAND}' not found on system.")
        self.connected = False
        return False

    async def send_command(self, command_name: str) -> bool:
        lirc_key = config.LIRC_KEY_MAP.get(command_name)
        if not lirc_key:
            raise ValueError(f"No LIRC mapping for command '{command_name}'.")

        loop = asyncio.get_running_loop()
        cmd = [config.LIRC_COMMAND, "SEND_ONCE", config.LIRC_REMOTE, lirc_key]
        try:
            res = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, text=True, check=True)
            )
            self.last_command = command_name
            logger.info(f"[LircBackend] Executed: {' '.join(cmd)}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"[LircBackend] irsend failed: {e.stderr}")
            raise RuntimeError(f"LIRC command failed: {e.stderr}") from e

    async def send_raw(self, code_str: str) -> bool:
        raise NotImplementedError("Direct raw hex IR sending is not supported on LIRC backend. Use mapped commands.")


# ==============================================================================
# Backend Auto-Detection and Factory
# ==============================================================================

async def create_backend() -> BaseIRBackend:
    """Detect and return the appropriate IR backend based on configuration & environment."""
    selected = config.IR_BACKEND

    if selected == "mock":
        backend = MockBackend()
        await backend.initialize()
        return backend

    if selected == "broadlink":
        backend = BroadlinkBackend()
        await backend.initialize()
        if not backend.connected:
            logger.warning("Broadlink selected but not connected. Falling back to mock backend.")
            mock = MockBackend()
            await mock.initialize()
            return mock
        return backend

    if selected in ("lirc", "gpio"):
        backend = LircBackend()
        await backend.initialize()
        if not backend.connected:
            logger.warning("LIRC/GPIO selected but irsend not found. Falling back to mock backend.")
            mock = MockBackend()
            await mock.initialize()
            return mock
        return backend

    # Auto mode:
    logger.info("Auto-detecting IR backend...")
    # 1. Try Broadlink
    if BROADLINK_AVAILABLE:
        broadlink_backend = BroadlinkBackend()
        if await broadlink_backend.initialize():
            logger.info("Auto-detected Broadlink backend.")
            return broadlink_backend

    # 2. Try LIRC / GPIO
    lirc_backend = LircBackend()
    if await lirc_backend.initialize():
        logger.info("Auto-detected LIRC/GPIO backend.")
        return lirc_backend

    # 3. Fallback to Mock
    logger.info("No physical IR hardware detected. Initializing Mock backend.")
    mock = MockBackend()
    await mock.initialize()
    return mock


# Global active backend reference & estimated receiver state
backend_instance: Optional[BaseIRBackend] = None
receiver_state = {
    "volume": 25,  # Estimated current volume (0-100)
    "muted": False,
    "power": True,
    "source": "hdmi1"
}


# ==============================================================================
# FastAPI Application & Lifespan
# ==============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    global backend_instance
    logger.info("Starting SonyHub IR Control Server...")
    backend_instance = await create_backend()
    logger.info(f"Active IR Backend: {backend_instance.name} (connected={backend_instance.connected})")
    yield
    logger.info("Shutting down IR Control Server...")


app = FastAPI(
    title="Sony Home Theater IR Control Server",
    description="REST API to control Sony AV receiver / home theater sound system via Broadlink RM4, Raspberry Pi GPIO, or Mock.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for all origins (frontend integrations like SonyHub)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# Request / Response Schemas
# ==============================================================================

class VolumeSetRequest(BaseModel):
    level: int = Field(..., ge=0, le=100, description="Target volume level (0 to 100)")


class SourceRequest(BaseModel):
    source: Literal["hdmi1", "hdmi2", "bluetooth", "optical"] = Field(
        ...,
        description="Input source to switch to ('hdmi1', 'hdmi2', 'bluetooth', 'optical')"
    )


class PresetRequest(BaseModel):
    preset: Literal["movie", "music", "gaming", "sports"] = Field(
        ...,
        description="Sound mode DSP preset ('movie', 'music', 'gaming', 'sports')"
    )


class RawSendRequest(BaseModel):
    code: str = Field(..., description="Raw IR code string (Base64 Broadlink packet or Hex)")


class StatusResponse(BaseModel):
    device: str
    connected: bool
    last_command: str
    estimated_volume: int


# Helper to get the backend or raise
def get_backend() -> BaseIRBackend:
    if backend_instance is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="IR backend is not initialized."
        )
    return backend_instance


# ==============================================================================
# Endpoints
# ==============================================================================

@app.get("/health", summary="Health check")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/ir/status", response_model=StatusResponse, summary="Get IR device status")
async def get_status():
    """Returns current IR device backend status and connectivity."""
    backend = get_backend()
    status_info = backend.get_status()
    status_info["estimated_volume"] = receiver_state["volume"]
    return status_info


@app.post("/ir/volume/up", summary="Volume Up")
async def volume_up():
    """Send volume up IR signal."""
    backend = get_backend()
    try:
        await backend.send_command("volume_up")
        receiver_state["volume"] = min(100, receiver_state["volume"] + 1)
        return {
            "status": "ok",
            "action": "volume_up",
            "device": backend.name,
            "estimated_volume": receiver_state["volume"]
        }
    except Exception as e:
        logger.error(f"Error executing volume up: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ir/volume/down", summary="Volume Down")
async def volume_down():
    """Send volume down IR signal."""
    backend = get_backend()
    try:
        await backend.send_command("volume_down")
        receiver_state["volume"] = max(0, receiver_state["volume"] - 1)
        return {
            "status": "ok",
            "action": "volume_down",
            "device": backend.name,
            "estimated_volume": receiver_state["volume"]
        }
    except Exception as e:
        logger.error(f"Error executing volume down: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ir/volume/set", summary="Set volume level")
async def volume_set(req: VolumeSetRequest):
    """
    Set target volume level (0-100).
    Sends repeated up/down pulses based on current estimated receiver volume.
    """
    backend = get_backend()
    target_level = req.level
    current = receiver_state["volume"]
    delta = target_level - current

    command = "volume_up" if delta > 0 else "volume_down"
    pulses = abs(delta)

    logger.info(f"Setting volume from {current} to {target_level} ({pulses} pulses of {command})...")

    try:
        for _ in range(pulses):
            await backend.send_command(command)
            # Brief pause between IR bursts to allow receiver decoding
            await asyncio.sleep(0.08)

        receiver_state["volume"] = target_level
        return {
            "status": "ok",
            "action": "volume_set",
            "target_level": target_level,
            "pulses_sent": pulses,
            "device": backend.name,
            "estimated_volume": target_level
        }
    except Exception as e:
        logger.error(f"Error during volume set: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ir/mute", summary="Toggle Mute")
async def toggle_mute():
    """Send mute toggle IR signal."""
    backend = get_backend()
    try:
        await backend.send_command("mute")
        receiver_state["muted"] = not receiver_state["muted"]
        return {
            "status": "ok",
            "action": "mute",
            "device": backend.name,
            "is_muted": receiver_state["muted"]
        }
    except Exception as e:
        logger.error(f"Error executing mute toggle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ir/power", summary="Toggle Power")
async def toggle_power():
    """Send power toggle IR signal."""
    backend = get_backend()
    try:
        await backend.send_command("power")
        receiver_state["power"] = not receiver_state["power"]
        return {
            "status": "ok",
            "action": "power",
            "device": backend.name,
            "power_state": receiver_state["power"]
        }
    except Exception as e:
        logger.error(f"Error executing power toggle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ir/source", summary="Switch Input Source")
async def switch_source(req: SourceRequest):
    """
    Switch input source.
    Supported: 'hdmi1', 'hdmi2', 'bluetooth', 'optical'.
    """
    backend = get_backend()
    command = req.source.lower()
    try:
        await backend.send_command(command)
        receiver_state["source"] = command
        return {
            "status": "ok",
            "action": "source",
            "source": command,
            "device": backend.name
        }
    except Exception as e:
        logger.error(f"Error executing source switch to {req.source}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ir/preset", summary="Select Sound Mode Preset")
async def select_preset(req: PresetRequest):
    """
    Send DSP sound mode key.
    Supported: 'movie', 'music', 'gaming', 'sports'.
    """
    backend = get_backend()
    preset_name = req.preset.lower()
    command = f"{preset_name}_mode"
    try:
        await backend.send_command(command)
        return {
            "status": "ok",
            "action": "preset",
            "preset": preset_name,
            "device": backend.name
        }
    except Exception as e:
        logger.error(f"Error selecting sound mode preset {req.preset}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ir/send", summary="Send Raw IR Code")
async def send_raw_code(req: RawSendRequest):
    """
    Send raw IR code (Base64 string or Hex).
    Advanced usage for custom or unmapped remotes.
    """
    backend = get_backend()
    try:
        await backend.send_raw(req.code)
        return {
            "status": "ok",
            "action": "raw_send",
            "device": backend.name
        }
    except NotImplementedError:
        raise HTTPException(
            status_code=400,
            detail="Raw IR code sending is not supported on the active backend (e.g. LIRC)."
        )
    except Exception as e:
        logger.error(f"Error sending raw IR code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.SERVER_HOST, port=config.SERVER_PORT)
