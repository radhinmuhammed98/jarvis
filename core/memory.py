import sqlite3
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "jarvis_memory.db")

import string

def normalize_key(key: str) -> str:
    """Normalizes memory keys for consistent lookup."""
    k = key.lower().strip()
    k = k.rstrip(string.punctuation)
    
    # Common mappings
    mappings = {
        "my name": "user_name",
        "name": "user_name",
        "my browser": "preferred_browser",
        "browser": "preferred_browser",
        "your name": "assistant_name"
    }
    
    return mappings.get(k, k)

def denormalize_key(key: str) -> str:
    """Converts normalized keys back to user-friendly labels."""
    reverse_mappings = {
        "user_name": "your name",
        "preferred_browser": "your preferred browser",
        "assistant_name": "my name"
    }
    return reverse_mappings.get(key, key)

def init_memory():
    """Initializes the SQLite database and creates the memories table if it doesn't exist."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                category TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("Memory database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize memory database: {e}")

def remember(key: str, value: str, category: str = "general") -> bool:
    """Stores or updates a key-value pair in memory."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        # Upsert logic (Insert or Replace)
        cursor.execute('''
            INSERT INTO memories (key, value, category, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value=excluded.value,
                category=excluded.category,
                updated_at=excluded.updated_at
        ''', (normalize_key(key), value.strip(), category, now, now))
        
        conn.commit()
        conn.close()
        logger.debug(f"Remembered: {key} -> {value}")
        return True
    except Exception as e:
        logger.error(f"Failed to remember '{key}': {e}")
        return False

def recall(key: str) -> str | None:
    """Retrieves a value from memory by key."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM memories WHERE key = ?', (normalize_key(key),))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        return None
    except Exception as e:
        logger.error(f"Failed to recall '{key}': {e}")
        return None

def forget(key: str) -> bool:
    """Deletes a key from memory."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM memories WHERE key = ?', (normalize_key(key),))
        changes = conn.total_changes
        conn.commit()
        conn.close()
        return changes > 0
    except Exception as e:
        logger.error(f"Failed to forget '{key}': {e}")
        return False

def list_memories() -> list[dict]:
    """Returns all stored memories."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM memories ORDER BY updated_at DESC')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to list memories: {e}")
        return []
