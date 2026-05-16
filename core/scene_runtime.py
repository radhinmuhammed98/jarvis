"""
core/scene_runtime.py
Parameterized, mutable background scene engine for Jarvis.

- All state is module-level and mutated live by the running thread.
- Pattern, speed, and duration can be changed while the scene is running.
- Thread polls state every loop iteration — no restart needed to change pattern/speed.
- Persist last scene config to SQLite via control_context so "again" works after restart.
"""
import threading
import time
import random
import logging

logger = logging.getLogger(__name__)

# ── Live-mutable scene state (read by thread every loop tick) ─────────────────
_lock = threading.Lock()
_stop_event: threading.Event = threading.Event()
_scene_thread: threading.Thread | None = None

# Mutable by API functions while thread runs
_devices: list[str] = []
_pattern: str = "chase"
_speed: float = 0.25       # seconds (lower = faster)
_duration: float | None = None   # None = infinite
_start_time: float = 0.0

_MIN_SPEED = 0.05
_MAX_SPEED = 2.0
_SPEED_STEP_FASTER = 0.05
_SPEED_STEP_SLOWER = 0.1

VALID_PATTERNS = [
    "chase", "blink_all", "alternate", "random_pulse", 
    "wave", "strobe", "single_random_pulse",
    "beat_pulse", "happy_birthday", "dracula"
]
_active_single_device: str | None = None


# ── Helper: non-blocking ESP command ─────────────────────────────────────────

def _cmd(device: str, command: str):
    """Send a single ESP32 command; log and continue on failure."""
    try:
        from modules.esp32.esp_client import _send_single_command
        _send_single_command(device, command)
    except Exception as e:
        logger.debug(f"[Scene] {device} {command} failed: {e}")


def _all(devices: list[str], command: str):
    for d in devices:
        _cmd(d, command)


def _isl(secs: float, stop_event: threading.Event) -> bool:
    """Interruptible sleep. Returns True if stopped early."""
    end = time.monotonic() + secs
    while time.monotonic() < end:
        if stop_event.is_set():
            return True
        time.sleep(0.015)
    return False


# ── Pattern implementations ────────────────────────────────────────────────────

def _pattern_chase(devs: list[str], stop: threading.Event):
    for d in devs:
        if stop.is_set(): return
        _cmd(d, "on")
        if _isl(_speed, stop): return
        _cmd(d, "off")
        if _isl(_speed * 0.3, stop): return


def _pattern_blink_all(devs: list[str], stop: threading.Event):
    _all(devs, "on")
    if _isl(_speed, stop): return
    _all(devs, "off")
    if _isl(_speed, stop): return


def _pattern_alternate(devs: list[str], stop: threading.Event):
    # Group A: first half ON, Group B: second half ON, alternating
    mid = max(1, len(devs) // 2)
    group_a = devs[:mid]
    group_b = devs[mid:]
    _all(group_a, "on")
    _all(group_b, "off")
    if _isl(_speed, stop): return
    _all(group_a, "off")
    _all(group_b, "on")
    if _isl(_speed, stop): return
    _all(group_b, "off")


def _pattern_random_pulse(devs: list[str], stop: threading.Event):
    d = random.choice(devs)
    _cmd(d, "on")
    dur = _speed * random.uniform(0.5, 1.5)
    if _isl(dur, stop): return
    _cmd(d, "off")
    if _isl(_speed * 0.2, stop): return


def _pattern_wave(devs: list[str], stop: threading.Event):
    # Turn on one by one, then off one by one
    for d in devs:
        if stop.is_set(): return
        _cmd(d, "on")
        if _isl(_speed * 0.5, stop): return
    for d in devs:
        if stop.is_set(): return
        _cmd(d, "off")
        if _isl(_speed * 0.5, stop): return


def _pattern_strobe(devs: list[str], stop: threading.Event):
    delay = max(_MIN_SPEED, _speed * 0.3)
    _all(devs, "on")
    if _isl(delay, stop): return
    _all(devs, "off")
    if _isl(delay, stop): return


def _pattern_single_random_pulse(devs: list[str], stop: threading.Event):
    global _active_single_device
    if not _active_single_device or _active_single_device not in devs:
        _active_single_device = random.choice(devs)
    
    _cmd(_active_single_device, "on")
    if _isl(_speed, stop): return
    _cmd(_active_single_device, "off")
    if _isl(_speed, stop): return


def _pattern_beat_pulse(devs: list[str], stop: threading.Event):
    _all(devs, "on")
    if _isl(0.15, stop): return
    _all(devs, "off")
    if _isl(0.25, stop): return


def _pattern_happy_birthday(devs: list[str], stop: threading.Event):
    rhythm = [0.25, 0.25, 0.5, 0.25, 0.25, 0.5, 0.25, 0.25, 0.25, 0.25, 0.7]
    for i, duration in enumerate(rhythm):
        d = devs[i % len(devs)]
        _cmd(d, "on")
        if _isl(duration, stop): return
        _cmd(d, "off")
        if _isl(0.05, stop): return


def _pattern_dracula(devs: list[str], stop: threading.Event):
    # Spooky red1 slow, red2 slow, blue quick flash
    if "red1" in devs:
        _cmd("red1", "on")
        if _isl(0.8, stop): return
        _cmd("red1", "off")
        if _isl(0.2, stop): return
    
    if "red2" in devs:
        _cmd("red2", "on")
        if _isl(0.8, stop): return
        _cmd("red2", "off")
        if _isl(0.2, stop): return

    if "blue" in devs:
        _cmd("blue", "on")
        if _isl(0.1, stop): return
        _cmd("blue", "off")
        if _isl(0.1, stop): return
        _cmd("blue", "on")
        if _isl(0.1, stop): return
        _cmd("blue", "off")
        if _isl(0.8, stop): return
    else:
        if _isl(1.0, stop): return


_PATTERN_FNS = {
    "chase":                _pattern_chase,
    "blink_all":            _pattern_blink_all,
    "alternate":            _pattern_alternate,
    "random_pulse":         _pattern_random_pulse,
    "wave":                 _pattern_wave,
    "strobe":               _pattern_strobe,
    "single_random_pulse":  _pattern_single_random_pulse,
    "beat_pulse":           _pattern_beat_pulse,
    "happy_birthday":       _pattern_happy_birthday,
    "dracula":              _pattern_dracula,
}


# ── Main scene thread ─────────────────────────────────────────────────────────

def _scene_loop(stop_event: threading.Event):
    global _duration, _start_time
    logger.info(f"[Scene] Thread started: pattern={_pattern} speed={_speed} devices={_devices}")
    _start_time = time.monotonic()

    while not stop_event.is_set():
        # Duration check
        if _duration is not None:
            if time.monotonic() - _start_time >= _duration:
                logger.info("[Scene] Duration elapsed, stopping.")
                break

        # Read live state each iteration
        devs    = list(_devices)
        pat     = _pattern

        fn = _PATTERN_FNS.get(pat, _pattern_chase)
        try:
            fn(devs, stop_event)
        except Exception as e:
            logger.debug(f"[Scene] Pattern error: {e}")
            time.sleep(0.05)

    # Clean up
    try:
        devs = list(_devices)
        _all(devs, "off")
    except Exception:
        pass
    logger.info("[Scene] Thread exited cleanly.")


# ── Public API ────────────────────────────────────────────────────────────────

def start_scene(
    devices: list[str],
    pattern: str = "chase",
    speed: float = 0.25,
    duration: float | None = None
) -> str:
    """Start a new background scene, stopping any running one first."""
    global _devices, _pattern, _speed, _duration, _stop_event, _scene_thread

    if not devices:
        return "No devices to animate."

    pattern = pattern if pattern in VALID_PATTERNS else "chase"
    speed   = max(_MIN_SPEED, min(_MAX_SPEED, speed))

    with _lock:
        if _scene_thread and _scene_thread.is_alive():
            _stop_event.set()
            _scene_thread.join(timeout=3)

        _stop_event  = threading.Event()
        _devices     = list(devices)
        _pattern     = pattern
        _speed       = speed
        _duration    = duration

        _scene_thread = threading.Thread(
            target=_scene_loop,
            args=(_stop_event,),
            daemon=True,
            name="JarvisSceneThread"
        )
        _scene_thread.start()

    _persist_scene()
    logger.info(f"[Scene] Started: pattern={pattern} speed={speed} duration={duration}")
    return "I started dancing the lights."


def stop_scene() -> str:
    global _scene_thread
    with _lock:
        if not _scene_thread or not _scene_thread.is_alive():
            return "No light scene is running."
        _stop_event.set()
        _scene_thread.join(timeout=4)
    logger.info("[Scene] Stopped by user.")
    return "I stopped the lights."


def is_scene_running() -> bool:
    return bool(_scene_thread and _scene_thread.is_alive() and not _stop_event.is_set())


def change_pattern(pattern: str) -> str:
    global _pattern, _active_single_device
    if pattern not in VALID_PATTERNS:
        return f"Unknown pattern '{pattern}'. Valid: {', '.join(VALID_PATTERNS)}."
    _pattern = pattern
    _active_single_device = None
    friendly = pattern.replace("_", " ")
    logger.info(f"[Scene] Pattern changed to {pattern}")
    return f"Changed to {friendly}."


def change_speed(speed: float) -> str:
    global _speed
    _speed = max(_MIN_SPEED, min(_MAX_SPEED, speed))
    return f"Speed set to {_speed:.2f}s delay."


def speed_up() -> str:
    global _speed
    if not is_scene_running():
        return "No light scene is running."
    new = max(_MIN_SPEED, _speed - _SPEED_STEP_FASTER)
    if new == _speed:
        return "Already at the fastest speed."
    _speed = new
    logger.info(f"[Scene] Speed up: delay={_speed:.2f}s")
    return "Speed increased."


def slow_down() -> str:
    global _speed
    if not is_scene_running():
        return "No light scene is running."
    new = min(_MAX_SPEED, _speed + _SPEED_STEP_SLOWER)
    if new == _speed:
        return "Already at the slowest speed."
    _speed = new
    logger.info(f"[Scene] Speed down: delay={_speed:.2f}s")
    return "Speed decreased."


def set_duration(seconds: float) -> str:
    global _duration, _start_time
    _duration   = seconds
    _start_time = time.monotonic()
    return f"Okay, I'll stop it after {int(seconds)} seconds."


def next_pattern() -> str:
    """Cycle to the next available pattern."""
    global _pattern, _active_single_device
    idx = VALID_PATTERNS.index(_pattern) if _pattern in VALID_PATTERNS else 0
    _pattern = VALID_PATTERNS[(idx + 1) % len(VALID_PATTERNS)]
    _active_single_device = None
    friendly = _pattern.replace("_", " ")
    logger.info(f"[Scene] Pattern cycled to {_pattern}")
    return f"Switched to {friendly}."


def repeat_last_scene() -> str:
    """Restart the last persisted scene."""
    cfg = _load_last_scene()
    if not cfg:
        return "I don't have a previous light scene yet."
    return start_scene(
        devices  = cfg["devices"],
        pattern  = cfg.get("pattern", "chase"),
        speed    = cfg.get("speed", 0.25),
        duration = cfg.get("duration"),
    )


def get_scene_status() -> str:
    if is_scene_running():
        dur_str = f", and will stop in {int(_duration - (time.monotonic() - _start_time))} seconds" if _duration else ""
        friendly_pattern = _pattern.replace("_", " ")
        return (
            f"The lights are dancing with the {friendly_pattern} pattern "
            f"at {_speed:.2f} seconds delay{dur_str}."
        )
    return "No scene is running."


# ── Persistence ───────────────────────────────────────────────────────────────

def _persist_scene():
    try:
        import json
        from core.control_context import set_context, set_last_action_type
        cfg = json.dumps({
            "devices":  _devices,
            "pattern":  _pattern,
            "speed":    _speed,
            "duration": _duration,
        })
        set_context("last_scene_config", cfg)
        set_last_action_type("scene")
    except Exception as e:
        logger.debug(f"[Scene] Could not persist scene: {e}")


def _load_last_scene() -> dict | None:
    try:
        import json
        from core.control_context import get_context
        raw = get_context("last_scene_config")
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None
