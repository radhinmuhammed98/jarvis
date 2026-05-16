import logging

logger = logging.getLogger(__name__)

DEVICES = {
    "light": {
        "type": "light",
        "esp32": "main",
        "endpoint": "light",
        "aliases": ["light", "main light", "room light", "velicham"]
    },
    "blue_light": {
        "type": "light",
        "esp32": "main",
        "endpoint": "blue_light",
        "aliases": ["blue light", "blue", "blue one", "neela light"]
    },
    "fan": {
        "type": "fan",
        "esp32": "main",
        "endpoint": "fan",
        "aliases": ["fan", "room fan"]
    },
    "plug": {
        "type": "plug",
        "esp32": "main",
        "endpoint": "plug",
        "aliases": ["plug", "socket"]
    }
}

def get_device(device_name: str) -> dict | None:
    return DEVICES.get(device_name)

def resolve_device(text: str) -> str | None:
    text_lower = text.lower()
    
    # Priority matches
    if "blue" in text_lower or "neela" in text_lower:
        return "blue_light"
    if "fan" in text_lower:
        return "fan"
    if "plug" in text_lower or "socket" in text_lower:
        return "plug"
    if "light" in text_lower or "velicham" in text_lower or "ligh" in text_lower:
        return "light"
        
    return None

def resolve_group(text: str) -> list[str] | None:
    text_lower = text.lower()
    
    # "all lights", "every light", "lights", "ella lightum"
    import re
    if re.search(r"\b(all\s+(the\s+)?lights?|every light|lights|ella lightum)\b", text_lower):
        return get_all_lights()
        
    if "everything" in text_lower or "all devices" in text_lower:
        return get_all_devices()
        
    return None

def get_devices_by_type(device_type: str) -> list[str]:
    return [name for name, info in DEVICES.items() if info.get("type") == device_type]

def get_all_devices() -> list[str]:
    return list(DEVICES.keys())

def get_all_lights() -> list[str]:
    return get_devices_by_type("light")
