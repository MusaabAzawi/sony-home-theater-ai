"""
Sony Remote IR Code Learning Tool for Broadlink RM4 Pro / Mini.

Enters learning mode on the Broadlink device, captures IR packets from
the physical Sony remote, and saves them to 'learned_codes.json'.

Usage:
    # Interactive mode (learn all standard commands):
    python ir_learn.py

    # Learn a single specific command:
    python ir_learn.py --command volume_up

    # List currently learned and default codes:
    python ir_learn.py --list

    # Test send a learned/mapped code:
    python ir_learn.py --test volume_up
"""

import sys
import time
import base64
import argparse
import logging
from typing import Optional, List

import config

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("ir_learn")

try:
    import broadlink
    BROADLINK_INSTALLED = True
except ImportError:
    BROADLINK_INSTALLED = False

# Standard list of commands to learn
COMMAND_DESCRIPTIONS = {
    "volume_up":   "VOLUME UP (Vol +)",
    "volume_down": "VOLUME DOWN (Vol -)",
    "mute":        "MUTE (Toggle mute)",
    "power":       "POWER (Toggle power on/off)",
    "hdmi1":       "HDMI 1 input source",
    "hdmi2":       "HDMI 2 input source",
    "bluetooth":   "BLUETOOTH (BT Audio input)",
    "optical":     "OPTICAL / TV input source",
    "movie_mode":  "MOVIE sound mode / DSP preset",
    "music_mode":  "MUSIC sound mode / DSP preset",
    "gaming_mode": "GAME sound mode / DSP preset",
    "sports_mode": "SPORTS sound mode / DSP preset",
}


def get_broadlink_device():
    """Discover or connect to Broadlink device."""
    if not BROADLINK_INSTALLED:
        print("\n[ERROR] The 'broadlink' package is not installed.")
        print("Please run: pip install broadlink\n")
        sys.exit(1)

    print("\n🔍 Searching for Broadlink IR Blaster...")

    device = None

    # Try configured IP first
    if config.BROADLINK_IP:
        print(f"Connecting to configured IP: {config.BROADLINK_IP}...")
        try:
            if hasattr(broadlink, "hello"):
                device = broadlink.hello(config.BROADLINK_IP)
        except Exception as e:
            print(f"Direct connection to {config.BROADLINK_IP} failed: {e}")

    # Fall back to discovery
    if not device:
        print(f"Scanning local network (timeout={config.BROADLINK_TIMEOUT}s)...")
        devices = broadlink.discover(timeout=config.BROADLINK_TIMEOUT)
        if devices:
            device = devices[0]

    if not device:
        print("\n❌ No Broadlink device discovered on your network!")
        print("Troubleshooting tips:")
        print(" 1. Ensure your Broadlink RM4 Pro is powered on and connected to the same WiFi network (2.4GHz).")
        print(" 2. In the Broadlink mobile app, open Device Settings -> Device Property -> turn OFF 'Lock Device'.")
        print(" 3. Explicitly set BROADLINK_IP=192.168.x.x in your .env file.\n")
        sys.exit(1)

    try:
        device.auth()
    except Exception as e:
        print(f"\n❌ Failed to authenticate with Broadlink device: {e}")
        print("If 'Lock Device' is enabled in the Broadlink app, local authentication will be rejected.")
        sys.exit(1)

    dev_name = getattr(device, "model", "Broadlink Device")
    dev_host = getattr(device, "host", ("Unknown", 0))[0]
    print(f" Connected to {dev_name} ({dev_host})\n")
    return device


def learn_single_command(device, command_name: str, description: str, timeout: int = 20) -> Optional[str]:
    """
    Put Broadlink into learning mode and capture the IR code.
    Returns the base64-encoded IR packet.
    """
    print("=" * 65)
    print(f"Target Command: {command_name.upper()} ({description})")
    print(f"👉 Point your Sony remote at the Broadlink and press {description.split('(')[0].strip()}... [waiting]")
    print("=" * 65)

    try:
        device.enter_learning()
    except Exception as e:
        print(f"❌ Failed to enter learning mode: {e}")
        return None

    start_time = time.time()
    spinner = ["|", "/", "-", "\\"]
    idx = 0

    while time.time() - start_time < timeout:
        remaining = int(timeout - (time.time() - start_time))
        sys.stdout.write(f"\rListening for IR signal {spinner[idx % len(spinner)]} ({remaining}s remaining)... ")
        sys.stdout.flush()
        idx += 1
        time.sleep(0.5)

        try:
            raw_data = device.check_data()
            if raw_data:
                b64_code = base64.b64encode(raw_data).decode("ascii")
                sys.stdout.write("\r" + " " * 60 + "\r")
                print(f" Captured IR code for '{command_name}'! ({len(raw_data)} bytes)")
                return b64_code
        except Exception:
            # Continue polling until timeout
            pass

    sys.stdout.write("\r" + " " * 60 + "\r")
    print(f"⏰ Timed out waiting for IR signal for '{command_name}'.")
    return None


def run_interactive_learning(device):
    """Interactively learn each standard command."""
    print("\n--- Sony Home Theater IR Learning Wizard ---")
    print("This will guide you through learning each Sony remote button.")
    print("Press Enter to begin, or Ctrl+C to exit at any time.\n")
    try:
        input("Press [Enter] to start...")
    except KeyboardInterrupt:
        print("\nExiting.")
        return

    learned_codes = config.load_learned_codes()
    commands = list(COMMAND_DESCRIPTIONS.keys())

    for cmd in commands:
        desc = COMMAND_DESCRIPTIONS[cmd]
        already_learned = cmd in learned_codes

        status_tag = "[Already Learned]" if already_learned else "[Not Learned]"
        print(f"\nNext: {cmd} - {desc} {status_tag}")
        ans = input(f"Learn this command? ([y]/n/skip/quit): ").strip().lower()

        if ans in ("q", "quit", "exit"):
            break
        if ans in ("n", "s", "skip"):
            continue

        while True:
            code = learn_single_command(device, cmd, desc)
            if code:
                learned_codes[cmd] = code
                config.save_all_learned_codes(learned_codes)
                print(f"💾 Saved '{cmd}' to {config.LEARNED_CODES_FILE.name}")
                break
            else:
                retry = input("Try again? ([y]/n): ").strip().lower()
                if retry == "n":
                    break

    print("\n All done! Learned codes saved to:", config.LEARNED_CODES_FILE)


def list_codes():
    """List default vs learned codes."""
    learned = config.load_learned_codes()
    defaults = config.SONY_IR_CODES

    print("\n" + "=" * 70)
    print(f"{'Command Name':<16} | {'Status':<15} | {'Code Preview'}")
    print("=" * 70)

    all_keys = sorted(set(list(defaults.keys()) + list(COMMAND_DESCRIPTIONS.keys()) + list(learned.keys())))
    for key in all_keys:
        if key in learned:
            status = " LEARNED"
            code_preview = learned[key][:25] + "..."
        elif key in defaults:
            status = "DEFAULT (MOCK)"
            code_preview = defaults[key][:25] + "..."
        else:
            status = "MISSING"
            code_preview = "N/A"

        print(f"{key:<16} | {status:<15} | {code_preview}")

    print("=" * 70)
    print(f"Total learned commands: {len(learned)}")
    print(f"Storage path: {config.LEARNED_CODES_FILE}\n")


def test_command(device, command_name: str):
    """Test send a learned or configured IR command."""
    codes = config.get_active_ir_codes()
    if command_name not in codes:
        print(f"❌ Unknown command '{command_name}'.")
        print(f"Available: {', '.join(codes.keys())}")
        return

    code_str = codes[command_name]
    print(f"🚀 Sending IR command '{command_name}' via {getattr(device, 'model', 'Broadlink')}...")
    try:
        raw_bytes = base64.b64decode(code_str)
        device.send_data(raw_bytes)
        print(" Sent successfully! Watch your Sony receiver for response.")
    except Exception as e:
        print(f"❌ Failed to send command: {e}")


def main():
    parser = argparse.ArgumentParser(description="Learn IR codes from your Sony remote using Broadlink RM4.")
    parser.add_argument("--command", "-c", type=str, help="Specific command to learn (e.g. volume_up, power)")
    parser.add_argument("--list", "-l", action="store_true", help="List current learned and default IR codes")
    parser.add_argument("--test", "-t", type=str, help="Test sending an IR command (e.g. volume_up)")
    args = parser.parse_args()

    if args.list:
        list_codes()
        return

    device = get_broadlink_device()

    if args.test:
        test_command(device, args.test)
        return

    if args.command:
        cmd = args.command.lower()
        desc = COMMAND_DESCRIPTIONS.get(cmd, f"Command: {cmd}")
        code = learn_single_command(device, cmd, desc)
        if code:
            config.save_learned_code(cmd, code)
            print(f"💾 Successfully saved '{cmd}' to {config.LEARNED_CODES_FILE}")
        else:
            print(f"❌ Failed to capture code for '{cmd}'.")
    else:
        # Full interactive mode
        run_interactive_learning(device)


if __name__ == "__main__":
    main()
