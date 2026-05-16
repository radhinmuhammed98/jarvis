import os
import requests
import tempfile
import logging
import sounddevice as sd
import numpy as np
import wave
from modules.voice.stt import listen_once

logger = logging.getLogger(__name__)

def record_audio_to_wav() -> str | None:
    """Records audio from microphone for a fixed duration and saves to a temp wav file."""
    try:
        duration = int(os.getenv("WHISPER_RECORD_SECONDS", "4"))
        sample_rate = 16000
        
        device_id_str = os.getenv("JARVIS_INPUT_DEVICE", "")
        device_id = int(device_id_str) if device_id_str.isdigit() else None

        if device_id is not None:
            logger.debug(f"Using input device ID: {device_id}")

        logger.info(f"Listening for {duration} seconds...")
        print(f"(Listening for {duration} seconds...)")
        
        recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate,
                           channels=1, dtype='int16', device=device_id)
        sd.wait()  # Wait until recording is finished
        
        print("(Recording complete. Transcribing...)")
        
        # Calculate RMS volume to detect silence
        rms = np.sqrt(np.mean(np.square(recording.astype(np.float32))))
        threshold = int(os.getenv("JARVIS_SILENCE_THRESHOLD", "500"))
        
        logger.debug(f"Audio RMS: {rms:.2f} (Threshold: {threshold})")
        if rms < threshold:
            print("No speech detected.")
            return None
        
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = tmp.name
        tmp.close()
        
        with wave.open(tmp_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 2 bytes for int16
            wf.setframerate(sample_rate)
            wf.writeframes(recording.tobytes())
            
        return tmp_path
            
    except Exception as e:
        logger.error(f"Error recording audio: {e}")
        return None

def transcribe_with_groq() -> str:
    """Record audio and transcribe using Groq Whisper."""
    audio_path = record_audio_to_wav()
    if not audio_path:
        return ""
        
    try:
        api_key = os.getenv("GROQ_API_KEY")
        model = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")
        
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment.")
            
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        with open(audio_path, "rb") as f:
            files = {"file": ("audio.wav", f, "audio/wav")}
            data = {"model": model, "language": "en"}
            response = requests.post(url, headers=headers, files=files, data=data, timeout=10)
            
        response.raise_for_status()
        text = response.json().get("text", "").strip()
        
        # Filter out short or hallucinated texts
        min_length = int(os.getenv("JARVIS_MIN_TRANSCRIPT_LENGTH", "2"))
        lower_text = text.lower().replace(".", "").replace(",", "").strip()
        
        if len(lower_text) < min_length or lower_text in ["thank you", "thanks", "you"]:
            logger.debug(f"Ignoring hallucinated/short transcript: '{text}'")
            return ""
            
        if text:
            logger.info(f"Groq STT recognized: {text}")
        return text
        
    except Exception as e:
        logger.warning(f"Groq STT failed ({e}). Falling back to Vosk...")
        return listen_once()
        
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
