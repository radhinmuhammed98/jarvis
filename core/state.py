"""
core/state.py
In-memory runtime state for Jarvis.
On write, mirrors persistent storage via control_context so context
survives restarts.
"""
LISTENING = True
LAST_DEVICE = None
LAST_DEVICE_GROUP = None
LAST_CONTROL_TYPE = None


def is_listening() -> bool:
    return LISTENING


def set_listening(value: bool):
    global LISTENING
    LISTENING = value


def set_control_context(device=None, group=None, control_type=None, command=None):
    """
    Sets the runtime context and persists it to SQLite.
    Pass device OR group (not both) to mark the active target.
    """
    global LAST_DEVICE, LAST_DEVICE_GROUP, LAST_CONTROL_TYPE

    try:
        from core.control_context import (
            set_last_device, set_last_group, set_last_command
        )
        if device:
            LAST_DEVICE = device
            LAST_DEVICE_GROUP = None
            set_last_device(device)
        if group:
            LAST_DEVICE_GROUP = group
            LAST_DEVICE = None
            set_last_group("group", group)
        if control_type:
            LAST_CONTROL_TYPE = control_type
        if command:
            set_last_command(command)
    except Exception:
        # Fallback: in-memory only if DB unavailable
        if device:
            LAST_DEVICE = device
            LAST_DEVICE_GROUP = None
        if group:
            LAST_DEVICE_GROUP = group
            LAST_DEVICE = None
        if control_type:
            LAST_CONTROL_TYPE = control_type


def get_control_context() -> dict:
    """
    Returns the current control context.
    Loads from SQLite if in-memory is empty (e.g. after restart).
    """
    global LAST_DEVICE, LAST_DEVICE_GROUP

    # Warm up from DB if memory is empty
    if LAST_DEVICE is None and LAST_DEVICE_GROUP is None:
        try:
            from core.control_context import get_last_device, get_last_group
            db_device = get_last_device()
            db_group  = get_last_group()
            if db_group:
                LAST_DEVICE_GROUP = db_group
            elif db_device:
                LAST_DEVICE = db_device
        except Exception:
            pass

    return {
        "device": LAST_DEVICE,
        "group":  LAST_DEVICE_GROUP,
        "type":   LAST_CONTROL_TYPE,
    }
