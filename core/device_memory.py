import sqlite3
import json
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "device_memory.db")

def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_device_memory():
    """Initializes the devices table and seeds initial legacy devices if empty."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT UNIQUE,
            display_name TEXT,
            type TEXT,
            color TEXT,
            endpoint TEXT,
            esp32_name TEXT DEFAULT 'main',
            aliases TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    conn.commit()
    
    # Check if empty
    cursor.execute('SELECT COUNT(*) FROM devices')
    if cursor.fetchone()[0] == 0:
        logger.info("Device memory is empty. Seeding devices...")
        add_device("red1", "red one", "light", "red1", color="red", aliases=["red one", "first red", "red light one", "red1"])
        add_device("red2", "red two", "light", "red2", color="red", aliases=["red two", "second red", "next red", "red light two", "red2"])
        add_device("blue", "blue light", "light", "blue", color="blue", aliases=["blue", "blue light", "blue one", "neela light"])
        
    conn.close()

def add_device(device_id, display_name, type, endpoint, color=None, aliases=None, esp32_name="main"):
    """Adds a new device to memory."""
    if aliases is None:
        aliases = []
    
    now = datetime.now().isoformat()
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO devices (device_id, display_name, type, color, endpoint, esp32_name, aliases, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (device_id, display_name, type, color, endpoint, esp32_name, json.dumps(aliases), now, now))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        logger.error(f"Device ID '{device_id}' already exists.")
        return False
    except Exception as e:
        logger.error(f"Error adding device: {e}")
        return False

def update_device(device_id, **fields):
    """Updates specific fields of an existing device."""
    if not fields:
        return False
        
    now = datetime.now().isoformat()
    fields["updated_at"] = now
    
    if "aliases" in fields and not isinstance(fields["aliases"], str):
        fields["aliases"] = json.dumps(fields["aliases"])
        
    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values())
    values.append(device_id)
    
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(f'UPDATE devices SET {set_clause} WHERE device_id = ?', values)
    conn.commit()
    conn.close()
    return True

def get_device(device_id) -> dict | None:
    """Gets a device by its exact device_id."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM devices WHERE device_id = ?', (device_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        d = dict(row)
        d["aliases"] = json.loads(d["aliases"]) if d["aliases"] else []
        return d
    return None

def list_devices() -> list[dict]:
    """Returns all known devices."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM devices')
    rows = cursor.fetchall()
    conn.close()
    
    devices = []
    for r in rows:
        d = dict(r)
        d["aliases"] = json.loads(d["aliases"]) if d["aliases"] else []
        devices.append(d)
    return devices

def delete_device(device_id) -> bool:
    """Deletes a device from memory."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM devices WHERE device_id = ?', (device_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def find_devices_by_type(device_type: str) -> list[str]:
    """Returns a list of device_ids matching a specific type."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT device_id FROM devices WHERE type = ?', (device_type,))
    rows = cursor.fetchall()
    conn.close()
    return [r["device_id"] for r in rows]

def find_devices_by_color(color: str) -> list[str]:
    """Returns a list of device_ids matching a specific color."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT device_id FROM devices WHERE color = ?', (color,))
    rows = cursor.fetchall()
    conn.close()
    return [r["device_id"] for r in rows]

def get_all_devices() -> list[str]:
    return [d["device_id"] for d in list_devices()]

def get_all_lights() -> list[str]:
    return find_devices_by_type("light")

def resolve_group(text: str) -> list[str] | None:
    """Resolves phrases like 'all lights' or 'red lights' to a list of device_ids."""
    text_lower = text.lower()
    
    import re
    if re.search(r"\b(all\s+(the\s+)?lights?|every light|lights|ella lightum)\b", text_lower):
        return ["red1", "red2", "blue"]
        
    if "red lights" in text_lower:
        return ["red1", "red2"]
        
    if "blue lights" in text_lower:
        return ["blue"]
        
    if "everything" in text_lower or "all devices" in text_lower:
        return get_all_devices()
        
    return None

def find_device_by_text(text: str) -> str | None:
    """Resolves text to a single device_id using strict priority matching."""
    import re
    text_lower = text.lower()
    devices = list_devices()
    
    # 1. Search aliases first
    for d in devices:
        for alias in d.get("aliases", []):
            if alias in text_lower:
                return d["device_id"]
                
    # 2. Search display_name
    for d in devices:
        if d["display_name"] and d["display_name"].lower() in text_lower:
            return d["device_id"]
            
    # 3. Search device_id directly
    for d in devices:
        if d["device_id"].lower() in text_lower:
            return d["device_id"]
            
    # 4. Fallback legacy typos
    if re.search(r"\b(ligh|lgith|ilight|velicham)\b", text_lower):
        if get_device("light"):
            return "light"
            
    return None
