"""
Jarvis Input Queue
Decouples user input from command processing so new messages can be typed at any time.
"""
import queue

_queue: queue.Queue = queue.Queue()


def add_input(text: str) -> None:
    """Add a text input to the processing queue."""
    _queue.put(text)


def get_next_input(timeout: float = 0.1):
    """
    Get the next input from the queue.
    Returns None if no input is available within the timeout.
    """
    try:
        return _queue.get(timeout=timeout)
    except queue.Empty:
        return None


def has_pending_inputs() -> bool:
    """Returns True if there are inputs waiting in the queue."""
    return not _queue.empty()


def clear_input_queue() -> int:
    """Clears all pending inputs. Returns the number of items cleared."""
    cleared = 0
    while not _queue.empty():
        try:
            _queue.get_nowait()
            cleared += 1
        except queue.Empty:
            break
    return cleared
