import sys
import os
import logging
import threading
import ctypes

os.environ["PYTHONWARNINGS"] = "ignore"

from dotenv import load_dotenv

# Suppress annoying ALSA Linux audio errors globally
try:
    ERROR_HANDLER_FUNC = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
    def py_error_handler(filename, line, function, err, fmt): pass
    c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
    asound = ctypes.cdll.LoadLibrary('libasound.so.2')
    asound.snd_lib_error_set_handler(c_error_handler)
except Exception:
    pass

# Load environment variables at the very beginning
load_dotenv()

from core.intent_parser import IntentParser
from core.executor import CommandExecutor
from core.input_queue import add_input, get_next_input, has_pending_inputs
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Global flag for clean shutdown
_stop_event = threading.Event()
# True when the processing thread is actively working
_is_busy = threading.Event()


class Jarvis:
    def __init__(self, voice_mode=False):
        self.voice_mode = voice_mode
        logger.info(f"Initializing Jarvis (Voice: {self.voice_mode})...")
        
        from core.memory import init_memory
        from core.device_memory import init_device_memory
        from core.control_context import init_control_context
        init_memory()
        init_device_memory()
        init_control_context()
        
        from core.conversation import load_history_from_db
        load_history_from_db(limit=20)
        
        self.parser = IntentParser()
        self.executor = CommandExecutor()
        
        if self.voice_mode:
            from modules.voice.voice_engine import VoiceEngine
            self.voice = VoiceEngine()
            
        logger.info("Jarvis initialized successfully.")

    # ------------------------------------------------------------------
    # Input Thread: always-on listener, never processes
    # ------------------------------------------------------------------
    def _input_thread_text(self):
        """Reads text from stdin and pushes to queue, always ready."""
        while not _stop_event.is_set():
            try:
                user_input = input("You: ")
            except (EOFError, KeyboardInterrupt):
                _stop_event.set()
                break
            
            user_input = user_input.strip()
            
            if not user_input:
                continue
            
            # Ignore copied transcript lines
            if user_input.lower().startswith("jarvis:"):
                continue
            
            if user_input.lower() == "exit":
                add_input(user_input)
                _stop_event.set()
                break
            
            # If busy, show queued feedback before adding
            if _is_busy.is_set() or has_pending_inputs():
                sys.stdout.write("\r\033[K")
                print(f"[Queued]: {user_input}")
                sys.stdout.write("You: ")
                sys.stdout.flush()
            
            add_input(user_input)

    # ------------------------------------------------------------------
    # Processing loop: runs on the main thread, one command at a time
    # ------------------------------------------------------------------
    def _process_input(self, user_input: str):
        """Parse, execute, respond to one input — called by processing loop."""
        from core.conversation import add_user_message, add_assistant_message
        from core.state import is_listening

        add_user_message(user_input)
        intent_data = self.parser.parse(user_input)

        if not is_listening():
            if intent_data.get("action") == "SET_LISTENING" and intent_data.get("value") is True:
                pass  # Allow execution to wake up
            else:
                print("(silent)")
                return None  # Not EXIT

        response = self.executor.execute(intent_data)

        if response == "ACTION_EXIT":
            return "ACTION_EXIT"

        sys.stdout.write("\r\033[K")
        print(f"Jarvis: {response}")
        sys.stdout.write("You: ")
        sys.stdout.flush()
        add_assistant_message(response)

        if self.voice_mode:
            self.voice.speak(response)
        else:
            from modules.voice.tts import speak
            speak(response)

        return response

    def run(self):
        from modules.voice.stt import is_voice_input_enabled

        if self.voice_mode:
            mode_str = "voice"
        elif is_voice_input_enabled():
            mode_str = "voice input"
        else:
            mode_str = "text"
            
        print(f"Jarvis {mode_str} mode started")
        logger.info(f"Jarvis is now running in {mode_str} mode.")

        if self.voice_mode:
            self.voice.speak("System online. I'm listening.")
        else:
            from modules.voice.tts import speak
            if is_voice_input_enabled():
                speak("System online. I'm listening.")
            else:
                speak("System online. Waiting for input.")

        # ---- Start input thread ----
        input_thread = threading.Thread(
            target=self._input_thread_text,
            daemon=True,
            name="JarvisInputThread"
        )
        input_thread.start()

        # ---- Processing loop (main thread) ----
        empty_retries = 0
        try:
            while not _stop_event.is_set():
                user_input = get_next_input(timeout=0.1)

                if user_input is None:
                    # Nothing to process yet — check voice if enabled
                    if not self.voice_mode and is_voice_input_enabled() and empty_retries < 3:
                        from modules.voice.stt import listen_once
                        from modules.voice.normalizer import normalize_speech_text

                        engine = os.getenv("JARVIS_STT_ENGINE", "vosk").lower()
                        if engine == "groq":
                            from modules.voice.groq_stt import transcribe_with_groq
                            voice_input = transcribe_with_groq()
                        else:
                            voice_input = listen_once()

                        if voice_input:
                            empty_retries = 0
                            voice_input = normalize_speech_text(voice_input)
                            print(f"You: {voice_input}")
                            add_input(voice_input)
                        else:
                            empty_retries += 1
                    continue

                # We have something to process
                _is_busy.set()
                # Try to clear the "You: " prompt line before printing status
                sys.stdout.write("\r\033[K")
                print(f"Processing: {user_input}")
                sys.stdout.write("You: ")
                sys.stdout.flush()

                try:
                    result = self._process_input(user_input)
                except (KeyboardInterrupt, EOFError):
                    _stop_event.set()
                    break
                except Exception as e:
                    logger.error(f"Error in Jarvis processing: {e}")
                    error_msg = "Oops, something went wrong. Let's try again."
                    print(f"Jarvis: {error_msg}")
                    if self.voice_mode:
                        self.voice.speak(error_msg)
                    else:
                        from modules.voice.tts import speak
                        speak(error_msg)
                finally:
                    _is_busy.clear()

                if result == "ACTION_EXIT":
                    _stop_event.set()
                    if self.voice_mode:
                        self.voice.speak("Goodbye!")
                    print("Jarvis: Goodbye!")
                    break

        except (KeyboardInterrupt, EOFError):
            _stop_event.set()

        print()
        logger.info("Shutting down Jarvis...")


if __name__ == "__main__":
    voice_mode = "--voice" in sys.argv
    jarvis = Jarvis(voice_mode=voice_mode)
    jarvis.run()
