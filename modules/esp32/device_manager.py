import json
import os

MAP_FILE = os.path.join(os.path.dirname(__file__), "device_map.json")

def save_device_mapping(name: str, pin: int):
    """Save a custom name to pin mapping."""
    mappings = load_device_mappings()
    mappings[name.lower()] = f"pin_{pin}"
    with open(MAP_FILE, "w") as f:
        json.dump(mappings, f, indent=4)
    return f"Got it! I've assigned {name} to pin {pin}."

def load_device_mappings():
    """Load all custom device mappings."""
    if not os.path.exists(MAP_FILE):
        return {}
    try:
        with open(MAP_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def resolve_device_name(name: str) -> str:
    """Check if a name is a custom assigned device."""
    mappings = load_device_mappings()
    return mappings.get(name.lower(), name)
