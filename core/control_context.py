"""
core/control_context.py
Persistent control context using SQLite.
Stores last_device, last_group, last_command across restarts.
"""
import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "control_context.db"


def _connect():
    return sqlite3.connect(str(DB_PATH))


def init_control_context():
    """Create the control_context table if it does not exist."""
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS control_context (
            key   TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Control context DB initialized.")


# ── Generic key/value ────────────────────────────────────────────────

def set_context(key: str, value: str):
    now = datetime.now().isoformat()
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO control_context (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
    """, (key, value, now))
    conn.commit()
    conn.close()


def get_context(key: str) -> str | None:
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM control_context WHERE key=?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def clear_context():
    conn = _connect()
    conn.execute("DELETE FROM control_context")
    conn.commit()
    conn.close()


# ── Typed helpers ────────────────────────────────────────────────────

def set_last_device(device_id: str):
    set_context("last_device", device_id)
    # Clearing group so device is the authoritative target
    set_context("last_group", "")


def get_last_device() -> str | None:
    return get_context("last_device") or None


def set_last_group(group_name: str, device_ids: list[str]):
    """group_name is a human label (e.g. 'all lights'); device_ids is the real list."""
    set_context("last_group", json.dumps(device_ids))
    set_context("last_group_name", group_name)
    # Clear single-device context when a group is the active target
    set_context("last_device", "")


def get_last_group() -> list[str] | None:
    raw = get_context("last_group")
    if not raw:
        return None
    try:
        ids = json.loads(raw)
        return ids if ids else None
    except (json.JSONDecodeError, TypeError):
        return None


def set_last_command(command: str):
    set_context("last_command", command)


def get_last_command() -> str | None:
    return get_context("last_command") or None


# ── Pending device (multi-turn clarification) ──────────────────────

def set_pending_device(device_id: str):
    """Store a device that was identified but needs an on/off command."""
    set_context("pending_device", device_id)


def get_pending_device() -> str | None:
    return get_context("pending_device") or None


def clear_pending_device():
    set_context("pending_device", "")


# ── Last controlled device (for troubleshooting) ──────────────────

def set_last_controlled(device_id: str, command: str):
    """Record the most recently executed device + command pair."""
    set_context("last_controlled_device", device_id)
    set_context("last_controlled_command", command)
    set_context("last_action_type", "device")


def get_last_controlled() -> tuple[str | None, str | None]:
    """Returns (device_id, command) or (None, None)."""
    return (
        get_context("last_controlled_device") or None,
        get_context("last_controlled_command") or None,
    )


def get_last_action_type() -> str | None:
    return get_context("last_action_type") or None


def set_last_action(action_type: str, intent_data: dict):
    """
    Persist the last successful meaningful action.
    action_type: 'device_command', 'batch_command', 'scene_command', 'status_query'
    """
    import json
    set_context("last_action_type", action_type)
    set_context("last_intent_json", json.dumps(intent_data))


def get_last_action() -> tuple[str | None, dict | None]:
    """Returns (action_type, intent_data)."""
    import json
    action_type = get_context("last_action_type")
    intent_json = get_context("last_intent_json")
    if not action_type or not intent_json:
        return None, None
    try:
        return action_type, json.loads(intent_json)
    except Exception:
        return action_type, None


def set_pending_intent(intent: dict):
    import json
    set_context("pending_intent_json", json.dumps(intent))


def get_pending_intent() -> dict | None:
    import json
    val = get_context("pending_intent_json")
    if not val:
        return None
    try:
        return json.loads(val)
    except Exception:
        return None


def clear_pending_intent():
    clear_context_key("pending_intent_json")
