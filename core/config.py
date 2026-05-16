import os

# Environment variables are loaded in main.py via load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "liquid/lfm-2.5-1.2b-instruct:free"
).strip()

AI_PROVIDER = os.getenv("AI_PROVIDER", "groq").lower().strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()

USE_AI_INTENT = os.getenv("USE_AI_INTENT", "true").lower() == "true"

JARVIS_VOICE_ENABLED = os.getenv("JARVIS_VOICE_ENABLED", "false").lower() == "true"
JARVIS_VOICE_NAME = os.getenv("JARVIS_VOICE_NAME", "en-US-AriaNeural")
JARVIS_VOICE_RATE = os.getenv("JARVIS_VOICE_RATE", "-5%")
