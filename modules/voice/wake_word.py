import os
import logging
import time

logger = logging.getLogger(__name__)

_porcupine = None
_recorder = None

def cleanup_wake_word():
    """Cleans up global recorder and porcupine instances."""
    global _porcupine, _recorder
    if _recorder is not None:
        _recorder.delete()
        _recorder = None
    if _porcupine is not None:
        _porcupine.delete()
        _porcupine = None

def wait_for_wake_word(stop_event) -> bool:
    """
    Blocks until the wake word (Jarvis) is detected or stop_event is set.
    Returns True if wake word was detected, False if stopped or error.
    """
    access_key = os.getenv("PORCUPINE_ACCESS_KEY")
    if not access_key:
        logger.error("PORCUPINE_ACCESS_KEY environment variable is not set.")
        logger.error("To use the wake word feature, get a free key from https://console.picovoice.ai/")
        time.sleep(5) # Delay slightly so we don't spam the log, but don't block the main thread forever.
        return False

    global _porcupine, _recorder
    try:
        import pvporcupine
        from pvrecorder import PvRecorder
    except ImportError:
        logger.error("pvporcupine or pvrecorder not installed.")
        return False

    # Initialize globally so we don't open/close the mic stream repeatedly in a loop
    if _porcupine is None or _recorder is None:
        try:
            _porcupine = pvporcupine.create(access_key=access_key, keywords=["jarvis"])
            device_index = -1
            device_id_str = os.getenv("JARVIS_INPUT_DEVICE", "")
            if device_id_str.isdigit():
                device_index = int(device_id_str)

            _recorder = PvRecorder(device_index=device_index, frame_length=_porcupine.frame_length)
            _recorder.start()
            logger.info("Listening for wake word 'Jarvis'...")
            print("\n(Listening for 'Jarvis'...)", end="", flush=True)
        except Exception as e:
            logger.error(f"Failed to initialize wake word detector: {e}")
            time.sleep(5)
            return False

    try:
        # Check a few frames to avoid blocking forever. If no wake word, return False
        # so the main thread can check the text queue, then it will call this again.
        # Since _recorder is persistent, it just reads the next frames.
        start_time = time.time()

        # Ensure recorder is reading if it was stopped
        if not _recorder.is_recording:
            _recorder.start()

        while not stop_event.is_set() and (time.time() - start_time) < 0.2:
            pcm = _recorder.read()
            keyword_index = _porcupine.process(pcm)

            if keyword_index >= 0:
                logger.info("Wake word detected!")
                # Stop recording so the main STT engine can access the microphone exclusively
                _recorder.stop()
                return True

    except Exception as e:
        logger.error(f"Wake word detection loop failed: {e}")
        time.sleep(2)

    return False
