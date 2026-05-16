import logging
import sqlite3
from core.memory import DB_PATH

logger = logging.getLogger(__name__)

# Global list to store conversation history
_history = []

def load_history_from_db(limit: int = 20):
    """Loads the recent conversation history from SQLite into memory."""
    global _history
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            SELECT role, content FROM conversation_history 
            ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        rows = c.fetchall()
        _history = [{"role": row[0], "content": row[1]} for row in reversed(rows)]
        logger.info(f"Loaded {len(_history)} past messages from database.")
    except Exception as e:
        logger.error(f"Failed to load conversation history from DB: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def _save_to_db(role: str, content: str):
    """Internal helper to save a single message to SQLite."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT INTO conversation_history (role, content) VALUES (?, ?)', (role, content))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to save message to DB: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def add_user_message(text: str):
    """Adds a user message to the conversation history."""
    if text:
        _history.append({"role": "user", "content": text})
        _save_to_db("user", text)

def add_assistant_message(text: str):
    """Adds an assistant message to the conversation history."""
    if text:
        _history.append({"role": "assistant", "content": text})
        _save_to_db("assistant", text)

def get_recent_messages(limit: int = 10) -> list[dict]:
    """Returns the most recent messages up to the limit."""
    return _history[-limit:] if _history else []

def clear_conversation():
    """Clears the short-term conversation history and deletes from SQLite."""
    _history.clear()
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('DELETE FROM conversation_history')
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to clear conversation DB: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
    logger.info("Conversation history cleared.")

def get_user_messages() -> list[str]:
    """Returns all user messages from the current conversation."""
    return [msg["content"] for msg in _history if msg["role"] == "user"]

def get_nth_user_message(n: int) -> str | None:
    """Returns the nth user message (1-indexed)."""
    user_msgs = get_user_messages()
    if 1 <= n <= len(user_msgs):
        return user_msgs[n-1]
    return None
