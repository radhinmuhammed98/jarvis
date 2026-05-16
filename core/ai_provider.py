import logging
import requests
from core.config import (
    AI_PROVIDER, 
    GROQ_API_KEY, 
    GROQ_MODEL, 
    OPENROUTER_API_KEY, 
    OPENROUTER_MODEL
)

logger = logging.getLogger(__name__)

def call_ai(messages: list[dict], temperature: float = 0.2) -> str:
    """
    Unified entry point to call the configured AI provider.
    Raises exceptions (like requests.exceptions.HTTPError) if the API fails, 
    so the caller can handle fallbacks or user messages.
    """
    provider = AI_PROVIDER
    
    logger.info(f"Using AI Provider: {provider.upper()}")
    
    if provider == "groq":
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set.")
            
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": GROQ_MODEL,
            "messages": messages,
            "temperature": temperature
        }
        logger.info(f"Using Groq model: {GROQ_MODEL}")
        
    elif provider == "openrouter":
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY is not set.")
            
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/JarvisAssistant",
            "X-Title": "Jarvis Desktop Assistant"
        }
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": messages,
            "temperature": temperature
        }
        logger.info(f"Using OpenRouter model: {OPENROUTER_MODEL}")
        
    else:
        raise ValueError(f"Unknown AI_PROVIDER: {provider}")

    # Make the request
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    
    response_data = response.json()
    return response_data['choices'][0]['message']['content'].strip()
