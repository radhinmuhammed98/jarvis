import logging

logger = logging.getLogger(__name__)

# In-memory state tracking
DEVICE_STATES = {
    "light": "unknown",
    "blue_light": "unknown",
    "fan": "unknown",
    "plug": "unknown"
}

def set_device_state(device: str, state: str):
    """Update the memory state of a specific device."""
    if device in DEVICE_STATES:
        # Normalize to just "on", "off", "unknown" if needed
        s = state.lower()
        if "on" in s: s = "on"
        elif "off" in s: s = "off"
        else: s = "unknown"
        DEVICE_STATES[device] = s
        logger.debug(f"Device state updated: {device} -> {s}")

def get_device_state(device: str) -> str:
    """Get the current state of a device."""
    return DEVICE_STATES.get(device, "unknown")

def get_devices_by_state(state: str, device_type: str = None) -> list[str]:
    """Return all devices matching a state, optionally filtered by type."""
    from core.device_registry import get_devices_by_type
    
    valid_devices = list(DEVICE_STATES.keys())
    if device_type:
        valid_devices = get_devices_by_type(device_type)
        
    return [dev for dev in valid_devices if DEVICE_STATES.get(dev) == state.lower()]

def list_device_states(device_type: str = None) -> dict:
    """Return a dictionary of all devices and their states, optionally filtered by type."""
    from core.device_registry import get_devices_by_type
    
    valid_devices = list(DEVICE_STATES.keys())
    if device_type:
        valid_devices = get_devices_by_type(device_type)
        
    return {dev: DEVICE_STATES.get(dev) for dev in valid_devices}
