import speech_recognition as sr
import pyttsx3
import logging

logger = logging.getLogger(__name__)

class VoiceEngine:
    def __init__(self):
        # Initialize TTS
        try:
            self.tts_engine = pyttsx3.init()
            # Set voice properties
            self.tts_engine.setProperty('rate', 170)  # Speed
            self.tts_engine.setProperty('volume', 1.0)  # Volume
        except Exception as e:
            logger.error(f"Failed to initialize TTS engine: {e}")
            self.tts_engine = None

        # Initialize STT
        self.recognizer = sr.Recognizer()
        try:
            self.microphone = sr.Microphone()
        except Exception as e:
            logger.error(f"Failed to initialize microphone: {e}")
            self.microphone = None

    def speak(self, text):
        """Convert text to speech."""
        if not text or text == "ACTION_EXIT":
            return
            
        logger.info(f"Jarvis speaking: {text}")
        if self.tts_engine:
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception as e:
                logger.error(f"TTS error: {e}")
        else:
            print(f"(Voice output unavailable) Jarvis: {text}")

    def listen(self):
        """Listen for microphone input and return text."""
        if not self.microphone:
            return None

        try:
            with self.microphone as source:
                logger.info("Listening...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                logger.info("Processing speech...")
                text = self.recognizer.recognize_google(audio)
                logger.info(f"You said: {text}")
                return text
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            logger.debug("Speech not understood")
            return None
        except sr.RequestError as e:
            logger.error(f"STT service error: {e}")
            return None
        except Exception as e:
            logger.error(f"Voice listen error: {e}")
            return None
