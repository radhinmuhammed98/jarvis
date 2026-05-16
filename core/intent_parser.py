import logging

logger = logging.getLogger(__name__)

class IntentParser:
    def __init__(self):
        # Initialize AI model or NLP library here (e.g., spacy, openai, etc.)
        pass

    def parse(self, text: str) -> dict:
        """
        Parses the user input and returns a structured dictionary representing the intent.
        """
        logger.debug(f"Parsing input: {text}")
        
        if not text.strip():
            return {"action": "CHAT", "message": ""}
            
        text_lower = text.lower().strip()
        
        if text_lower in ["exit", "quit", "stop", "close", "bye", "goodbye"]:
            return {"action": "EXIT"}
            
        # Direct app name matching
        if text_lower in ["whatsapp", "youtube", "google", "firefox", "terminal", "files", "chrome", "browser"]:
            return {"action": "OPEN_APP", "target": text_lower}
            
        if text_lower.startswith("open "):
            target = text_lower[5:].strip()
            # Map common aliases
            if target == "internet":
                target = "browser"
            return {"action": "OPEN_APP", "target": target}
            
        if text_lower.startswith("search "):
            query = text_lower[7:].strip()
            return {"action": "SEARCH_WEB", "query": query}
            
        if "time is it" in text_lower or "what time" in text_lower or text_lower == "time":
            return {"action": "GET_TIME"}
            
        if "system info" in text_lower or "system status" in text_lower:
            return {"action": "SYSTEM_INFO"}
            
        # ESP32 light control - Wide Device Control
        import re
        from core.state import get_control_context

        # Check for status queries
        if text_lower in ["what is on", "which device is on"]:
            return {"action": "DEVICE_STATUS_QUERY", "state": "on"}
        if "which light" in text_lower or "what light" in text_lower or "which lights" in text_lower:
            return {"action": "DEVICE_STATUS_QUERY", "device_type": "light", "state": "on"}

        # 1. Determine Delay (Sequence)
        delay = 0
        if any(phrase in text_lower for phrase in ["one by one", "gap", "gaping", "gap a second"]):
            delay = 1

        # 2. Command Extraction
        command = None
        if re.search(r"\b(on|kathikkoo|kathik)\b", text_lower):
            command = "on"
        elif re.search(r"\b(off|keduthu|keduth)\b", text_lower) or "ito ff" in text_lower:
            command = "off"
        elif re.search(r"\b(status|state|check|undo)\b", text_lower):
            command = "status"
        elif "turn" in text_lower and delay > 0:
            command = "on"

        # 3. Target Matching via Registry
        from core.device_registry import resolve_group, resolve_device
        resolved_group = resolve_group(text_lower)
        resolved_device = resolve_device(text_lower)
        context = get_control_context()
        
        # Follow-up: "blue one only"
        if "only" in text_lower and resolved_device == "blue_light":
            return {"action": "SCENE_COMMAND", "scene": "blue_only"}

        # Pronouns
        if re.search(r"\b(it|them)\b|ito ff", text_lower):
            if not command: return {"action": "CHAT", "message": text}
            
            if "them" in text_lower or delay > 0:
                group = context.get("group") or ["light", "blue_light"]
                return {"action": "BATCH_DEVICE_COMMAND", "devices": group, "command": command, "delay": delay}
            else:
                device = context.get("device")
                if not device:
                    return {"action": "CHAT_LOCAL", "response": "Which device should I control?"}
                return {"action": "ESP32_COMMAND", "device": device, "command": command}

        # Explicit Group Match
        if resolved_group:
            if command:
                return {"action": "BATCH_DEVICE_COMMAND", "devices": resolved_group, "command": command, "delay": delay}

        # Explicit Single Match
        if resolved_device:
            if command:
                return {"action": "ESP32_COMMAND", "device": resolved_device, "command": command}
                
        # Sequence fallback
        if delay > 0 and command:
            group = context.get("group") or ["light", "blue_light"]
            return {"action": "BATCH_DEVICE_COMMAND", "devices": group, "command": command, "delay": delay}
                
        # Local memory handling
        if text_lower in ["show memory", "list memory"]:
            return {"action": "LIST_MEMORY"}
            
        if text_lower in ["clear chat", "reset chat"]:
            return {"action": "CLEAR_CONVERSATION"}
            
        if text_lower in ["delete all memory", "clear memory", "forget everything", "delete all memories"]:
            return {"action": "CLEAR_MEMORY"}

        silent_phrases = ["don't listen", "dont listen", "stop listening", "be quiet", "stay silent"]
        if any(phrase in text_lower for phrase in silent_phrases):
            return {"action": "SET_LISTENING", "value": False}
            
        wake_phrases = ["listen to me", "start listening", "wake up", "jarvis listen", "talk to me", "stop silent"]
        if any(phrase in text_lower for phrase in wake_phrases):
            return {"action": "SET_LISTENING", "value": True}
            
        if text_lower in ["what questions did i ask", "what are the questions i asked you", "what were my questions", "what did i ask"]:
            return {"action": "LIST_USER_MESSAGES"}
            
        import re
        match = re.match(r"what was my (first|second|third|1st|2nd|3rd) (message|question)", text_lower)
        if match:
            ordinals = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3}
            idx = ordinals.get(match.group(1))
            if idx:
                return {"action": "RECALL_USER_MESSAGE", "index": idx}
            
        if text_lower.startswith("remember "):
            if " is " in text_lower:
                idx = text_lower.find(" is ")
                key = text_lower[9:idx].strip()
                value = text[idx + 4:].strip()
                return {"action": "REMEMBER", "key": key, "value": value, "category": "general"}
            elif ":" in text_lower:
                idx = text_lower.find(":")
                key = text_lower[9:idx].strip()
                value = text[idx + 1:].strip()
                return {"action": "REMEMBER", "key": key, "value": value, "category": "general"}
            elif "=" in text_lower:
                idx = text_lower.find("=")
                key = text_lower[9:idx].strip()
                value = text[idx + 1:].strip()
                return {"action": "REMEMBER", "key": key, "value": value, "category": "general"}
            
        if text_lower.startswith("what is ") or text_lower.startswith("what's "):
            prefix_len = 8 if text_lower.startswith("what is ") else 7
            key = text_lower[prefix_len:].strip()
            # Prevent "what is your name" from being caught here if it's meant for local small-talk
            if key not in ["your name"]:
                return {"action": "RECALL", "key": key}
                
        if text_lower.startswith("forget "):
            key = text_lower[7:].strip()
            return {"action": "FORGET", "key": key}

        # Local small-talk handling
        if text_lower in ["hi", "hii", "hey", "heyy", "hyy", "hello", "yo", "bro"]:
            return {"action": "CHAT_LOCAL", "response": "Hello Radhin. How can I help?"}
            
        if text_lower in ["haha", "lol", "ok", "okay"]:
            return {"action": "CHAT_LOCAL", "response": "Alright."}
            
        if text_lower in ["thanks", "thank you"]:
            return {"action": "CHAT_LOCAL", "response": "Anytime."}
            
        if text_lower in ["whats ur name", "what is your name", "who are you"]:
            return {"action": "CHAT_LOCAL", "response": "I am Jarvis, your local assistant."}

        # Fallback to AI parsing if enabled, otherwise CHAT
        from core.config import USE_AI_INTENT
        if USE_AI_INTENT:
            from core.ai_intent_parser import parse_with_ai
            return parse_with_ai(text)
            
        return {"action": "CHAT", "message": text}
