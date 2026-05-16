import sys
import os
import logging
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
from utils.logger import setup_logger

logger = setup_logger(__name__)

class Jarvis:
    def __init__(self, voice_mode=False):
        self.voice_mode = voice_mode
        logger.info(f"Initializing Jarvis (Voice: {self.voice_mode})...")
        
        from core.memory import init_memory
        init_memory()
        
        from core.conversation import load_history_from_db
        load_history_from_db(limit=20)
        
        self.parser = IntentParser()
        self.executor = CommandExecutor()
        
        if self.voice_mode:
            from modules.voice.voice_engine import VoiceEngine
            self.voice = VoiceEngine()
            
        logger.info("Jarvis initialized successfully.")

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

        empty_retries = 0
        try:
            while True:
                try:
                    # Get user input
                    if self.voice_mode:
                        user_input = self.voice.listen()
                        if not user_input:
                            continue
                    else:
                        from modules.voice.stt import is_voice_input_enabled, listen_once
                        from modules.voice.normalizer import normalize_speech_text
                        import os
                        
                        if is_voice_input_enabled() and empty_retries < 3:
                            engine = os.getenv("JARVIS_STT_ENGINE", "vosk").lower()
                            if engine == "groq":
                                from modules.voice.groq_stt import transcribe_with_groq
                                user_input = transcribe_with_groq()
                            else:
                                user_input = listen_once()
                                
                            if user_input:
                                empty_retries = 0
                                user_input = normalize_speech_text(user_input)
                                print(f"You: {user_input}")
                            else:
                                empty_retries += 1
                                if empty_retries >= 3:
                                    print("I couldn't hear anything. Switching to text input for now.")
                                continue
                        else:
                            user_input = input("You: ")
                            if user_input:
                                empty_retries = 0
                        
                    if not user_input:
                        continue
                        
                    user_input = user_input.strip()
                    
                    # Ignore copied transcript lines
                    if user_input.lower().startswith("jarvis:"):
                        continue
                        
                    if not user_input:
                        continue
                        
                    from core.conversation import add_user_message, add_assistant_message
                    from core.state import is_listening
                    
                    add_user_message(user_input)
                        
                    # Send input to parse
                    intent_data = self.parser.parse(user_input)
                    
                    if not is_listening():
                        if intent_data.get("action") == "SET_LISTENING" and intent_data.get("value") is True:
                            pass # Allow execution to wake up
                        else:
                            print("(silent)")
                            continue
                    
                    # Send parsed intent to execute
                    response = self.executor.execute(intent_data)
                    
                    # Exit cleanly if action is EXIT
                    if response == "ACTION_EXIT":
                        if self.voice_mode:
                            self.voice.speak("Goodbye!")
                        print("Jarvis: Goodbye!")
                        break
                        
                    # Provide response
                    print(f"Jarvis: {response}")
                    add_assistant_message(response)
                    if self.voice_mode:
                        self.voice.speak(response)
                    else:
                        from modules.voice.tts import speak
                        speak(response)
                        
                except (KeyboardInterrupt, EOFError):
                    raise
                except Exception as e:
                    logger.error(f"Error in Jarvis loop: {e}")
                    error_msg = "Oops, something went wrong. Let's try again."
                    print(f"Jarvis: {error_msg}")
                    if self.voice_mode:
                        self.voice.speak(error_msg)
                    else:
                        from modules.voice.tts import speak
                        speak(error_msg)
                
        except (KeyboardInterrupt, EOFError):
            print()
            logger.info("Shutting down Jarvis...")

if __name__ == "__main__":
    voice_mode = "--voice" in sys.argv
    jarvis = Jarvis(voice_mode=voice_mode)
    jarvis.run()
