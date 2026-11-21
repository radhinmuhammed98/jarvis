import logging
import os
import json

logger = logging.getLogger(__name__)


def is_voice_input_enabled() -> bool:
    return os.getenv("JARVIS_VOICE_INPUT_ENABLED", "false").lower() == "true"


def listen_once() -> str:
    """Delegates to the preferred STT engine (Groq by default) for a single command capture."""
    engine = os.getenv("JARVIS_STT_ENGINE", "groq").lower()

    if engine == "groq":
        from modules.voice.groq_stt import transcribe_with_groq
        return transcribe_with_groq()
    else:
        return _listen_once_vosk()

def _listen_once_vosk() -> str:
    """Open microphone, listen for one utterance using Vosk, and return recognized text."""
    try:
        from vosk import Model, KaldiRecognizer
        import sounddevice as sd
    except ImportError as e:
        logger.error(f"Missing dependency for STT: {e}. Run: pip install vosk sounddevice")
        return ""

    model_path = os.getenv("JARVIS_STT_MODEL_PATH", "models/vosk-model-small-en-us-0.15")
    sample_rate = int(os.getenv("JARVIS_STT_SAMPLE_RATE", "16000"))

    if not os.path.exists(model_path):
        logger.error(f"Vosk model not found at '{model_path}'. Download from https://alphacephei.com/vosk/models")
        return ""

    try:
        model = Model(model_path)
        recognizer = KaldiRecognizer(model, sample_rate)
        recognizer.SetWords(True)
    except Exception as e:
        logger.error(f"Failed to load Vosk model: {e}")
        return ""

    device_id_str = os.getenv("JARVIS_INPUT_DEVICE", "")
    device_id = int(device_id_str) if device_id_str.isdigit() else None
    if device_id is not None:
        logger.debug(f"Using input device ID: {device_id}")

    logger.info("Listening (Vosk)...")
    print("\n(Listening...)")

    try:
        with sd.RawInputStream(samplerate=sample_rate, blocksize=8000,
                               device=device_id, dtype="int16", channels=1) as stream:
            # We add a slight timeout logic so we don't block forever if they don't say anything
            # after waking up. For simplicity, we just listen until a phrase is caught.
            while True:
                data, _ = stream.read(4000)
                if recognizer.AcceptWaveform(bytes(data)):
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "").strip()
                    if text:
                        logger.info(f"Vosk recognized: {text}")
                        return text
                    return ""
    except Exception as e:
        logger.error(f"Vosk listen_once() failed: {e}")
        return ""
