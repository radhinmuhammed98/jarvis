LISTENING = True
LAST_DEVICE = None
LAST_DEVICE_GROUP = None
LAST_CONTROL_TYPE = None

def is_listening() -> bool:
    return LISTENING

def set_listening(value: bool):
    global LISTENING
    LISTENING = value

def set_control_context(device=None, group=None, control_type=None):
    """Sets the context for the last commanded device or group."""
    global LAST_DEVICE, LAST_DEVICE_GROUP, LAST_CONTROL_TYPE
    if device:
        LAST_DEVICE = device
    if group:
        LAST_DEVICE_GROUP = group
    if control_type:
        LAST_CONTROL_TYPE = control_type

def get_control_context():
    """Returns the context as a dict."""
    return {
        "device": LAST_DEVICE,
        "group": LAST_DEVICE_GROUP,
        "type": LAST_CONTROL_TYPE
    }
