"""
core/scenes.py
Light animation / scene system for Jarvis.
"""
import time
import logging

logger = logging.getLogger(__name__)


def run_dance_scene(devices: list[str], cycles: int = 3, delay: float = 0.25) -> str:
    """
    Animate a list of devices in a repeating on/off chase pattern.

    Steps:
    1. Turn all devices OFF.
    2. For each cycle:
       a. Turn each device ON one by one (with delay).
       b. Turn each device OFF one by one (with delay).
    3. Return summary string.
    """
    from modules.esp32.esp_client import _send_single_command

    if not devices:
        return "No devices to animate."

    # Reset all to off first
    for dev in devices:
        _send_single_command(dev, "off")
    time.sleep(delay)

    for _ in range(cycles):
        # Chase ON
        for dev in devices:
            _send_single_command(dev, "on")
            time.sleep(delay)
        # Chase OFF
        for dev in devices:
            _send_single_command(dev, "off")
            time.sleep(delay)

    logger.info(f"Dance scene finished on: {devices}")
    return "I danced the lights."
