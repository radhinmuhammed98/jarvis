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
        
        if text_lower in ["exit", "quit", "close", "bye", "goodbye"]:
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

        # Check for debug commands
        if text_lower in ["test devices", "ping devices", "check endpoints"]:
            return {"action": "TEST_DEVICES"}

        # ── Troubleshooting: "it's not working" → check last device ────────
        TROUBLESHOOT_PHRASES = [
            "its not", "it's not", "not working", "it didnt",
            "didn't work", "didnt work", "not on", "not off", "its not working",
            "it's not working", "still not working", "still off", "still on",
            "lol its not", "lol it's not", "fix it", "fix this", "fix that"
        ]
        if any(text_lower == p or text_lower.endswith(p) for p in TROUBLESHOOT_PHRASES):
            return {"action": "VERIFY_LAST_DEVICE"}

        # Check for status queries
        if text_lower in ["what is on", "which device is on", "status", "light status", "device status"]:
            return {"action": "DEVICE_STATUS_QUERY", "state": "on"}
        if "which light" in text_lower or "what light" in text_lower or "which lights" in text_lower:
            return {"action": "DEVICE_STATUS_QUERY", "device_type": "light", "state": "on"}

        # ── Scene controls (all caught BEFORE AI, no fallthrough) ────────────
        # ── Scene controls (all caught BEFORE AI, no fallthrough) ────────────
        import re

        # STOP (checked first so "stop dancing" never triggers dance)
        STOP_PHRASES = [
            "stop", "stop dancing", "stop lights", "stop the lights",
            "stop dance", "enough", "mathi", "niruth", "niruthikko",
            "lights stop", "stop it", "pause lights"
        ]
        if text_lower in STOP_PHRASES:
            return {"action": "STOP_SCENE"}

        # DURATION: "stop after 5 seconds" / "off after 5 s"
        dur_match = re.search(
            r"(?:stop|off|end|finish).*?(\d+(?:\.\d+)?)\s*s(?:ec(?:onds?)?)?",
            text_lower
        )
        if dur_match:
            return {"action": "SCENE_DURATION", "seconds": float(dur_match.group(1))}

        # REPEAT
        REPEAT_PHRASES = ["do them again", "do it again", "again", "repeat", "run again", "one more time"]
        if text_lower in REPEAT_PHRASES:
            return {"action": "REPEAT_LAST_ACTION"}

        # STATUS / EXPLANATION
        STATUS_PHRASES = ["means?", "what do you mean", "what scene", "current scene", "status of lights", "light show status"]
        if text_lower in STATUS_PHRASES:
            return {"action": "SCENE_STATUS"}

        EXPLAIN_PHRASES = [
            "who said to dance", "why are you dancing", "i didn't say dance",
            "i didnt say dance", "why lights dancing", "who started this"
        ]
        if text_lower in EXPLAIN_PHRASES:
            return {"action": "SCENE_EXPLAIN"}

        CHOOSE_PHRASES = [
            "choose one", "u can choose one", "you can choose one",
            "based on my last", "you choose", "choose any light", "choose a light",
            "you pick", "pick one", "pick a light"
        ]
        if text_lower in CHOOSE_PHRASES:
            return {"action": "CHOOSE_DEVICE"}

        # SPEED
        FASTER_PHRASES = [
            "faster", "a bit faster", "more", "more more", "dance faster", "speed up", "go faster",
            "do it faster", "make it faster", "blink faster", "speed it up"
        ]
        SLOWER_PHRASES = [
            "slower", "a bit slower", "dance slower", "slow down", "go slower",
            "do it slower", "make it slower", "blink slower", "slow it down"
        ]
        if text_lower in FASTER_PHRASES:
            return {"action": "SCENE_SPEED", "direction": "faster"}
        if text_lower in SLOWER_PHRASES:
            return {"action": "SCENE_SPEED", "direction": "slower"}

        # PATTERN CHANGE (explicit)
        PATTERN_MAP = {
            "chase":                ["chase", "chase pattern", "do chase"],
            "blink_all":            ["blink all", "blink all lights", "blink them all"],
            "alternate":            ["alternate", "alternating", "do alternate"],
            "random_pulse":         ["random", "random pulse", "blink random pulse",
                                     "i want random pulse", "pulse", "random it"],
            "wave":                 ["wave", "wave pattern", "do wave"],
            "strobe":               ["strobe", "strobe lights", "strobe mode"],
            "single_random_pulse":  ["blink only one light", "blink one light", "one light pulse", "single light blink"],
            "beat_pulse":           ["beat", "dance in beat", "dance in the beats", "dance with beat", "music mode", "song mode"],
            "happy_birthday":       ["happy birthday", "happybirhtfay", "happy birthday song"],
            "dracula":              ["dracula", "spooky", "horror mode"],
        }
        for pat, phrases in PATTERN_MAP.items():
            if text_lower in phrases:
                return {"action": "SCENE_PATTERN", "pattern": pat}

        if "one light faster" in text_lower or "blink only one light faster" in text_lower:
             return {"action": "SCENE_PATTERN", "pattern": "single_random_pulse", "speed_direction": "faster"}

        NEXT_PATTERN_PHRASES = ["another pattern", "change pattern", "just change it",
                                "next pattern", "different pattern", "switch pattern"]
        if text_lower in NEXT_PATTERN_PHRASES:
            return {"action": "SCENE_NEXT_PATTERN"}

        # START DANCE
        DANCE_ALL = [
            "dance lights", "dance the lights", "make lights dance",
            "make the lights dance", "blink lights", "party mode", "disco mode",
            "start scene", "start lights", "light show"
        ]
        DANCE_LAST = ["dance it", "dance them", "make it dance", "make them dance"]
        
        # Fuzzy Typo Handling for START_SCENE
        is_dance_typo = ("danc" in text_lower and "light" in text_lower) or \
                        ("party" in text_lower and "light" in text_lower) or \
                        ("blink" in text_lower and "light" in text_lower)

        if any(p in text_lower for p in DANCE_ALL) or is_dance_typo:
            return {"action": "START_SCENE", "scene": "dance", "target": "ALL_LIGHTS", "pattern": "chase"}
        if any(p in text_lower for p in DANCE_LAST):
            return {"action": "START_SCENE", "scene": "dance", "target": "LAST_TARGET", "pattern": "chase"}


        # ── Command-only phrases (no explicit device) ─────────────────────
        # Check pending device FIRST — if user said "turn blue light" then "on",
        # the pending device should be used before falling back to CONTROL_LAST_TARGET.
        from core.control_context import get_pending_device
        pending = get_pending_device()

        COMMAND_ONLY_ON = [
            "on", "turn on", "switch on", "on it", "turn it on", "lights on",
            "put it on", "switch it on"
        ]
        COMMAND_ONLY_OFF = [
            "off", "turn off", "switch off", "off it", "turn it off", "lights off",
            "put it off", "switch it off"
        ]
        # Exact-match only so we don't eat "turn on the blue light" etc.
        if text_lower in COMMAND_ONLY_ON:
            if pending:
                return {"action": "ESP32_COMMAND", "device": pending, "command": "on", "_clear_pending": True}
            return {"action": "CONTROL_LAST_TARGET", "command": "on"}
        if text_lower in COMMAND_ONLY_OFF:
            if pending:
                return {"action": "ESP32_COMMAND", "device": pending, "command": "off", "_clear_pending": True}
            return {"action": "CONTROL_LAST_TARGET", "command": "off"}

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
        from core.device_memory import resolve_group, find_device_by_text, get_all_devices
        resolved_group = resolve_group(text_lower)
        resolved_device = find_device_by_text(text_lower)
        context = get_control_context()
        
        # Next One logic
        if text_lower in ["next one", "the next one", "next"]:
            group = context.get("group")
            current_device = context.get("device")
            if group and current_device and current_device in group:
                try:
                    idx = group.index(current_device)
                    if idx + 1 < len(group):
                        next_device = group[idx + 1]
                        return {"action": "ESP32_COMMAND", "device": next_device, "command": command or "on"}
                except ValueError:
                    pass
            return {"action": "CHAT_LOCAL", "response": "I don't know which next device you mean."}
        
        # Follow-up: "blue one only"
        if "only" in text_lower and resolved_device == "blue":
            return {"action": "SCENE_COMMAND", "scene": "blue_only"}
        if "only" in text_lower and resolved_group == ["red1", "red2"]:
            return {"action": "SCENE_COMMAND", "scene": "red_only"}
        if "red only" in text_lower:
            return {"action": "SCENE_COMMAND", "scene": "red_only"}

        # ── Control-verb guard ────────────────────────────────────────────
        # Only route to device control if the input actually looks like a
        # control request. Without a verb, fall through to CHAT.
        CONTROL_VERBS = {
            "turn", "switch", "on", "off", "start", "stop",
            "blink", "dance", "control", "kathikkoo", "kathik",
            "keduthu", "keduth"
        }
        has_control_verb = bool(command) or any(v in text_lower.split() for v in CONTROL_VERBS)

        # Clarification when a device/group is named but no command given —
        # only ask if the user clearly meant to control something.
        if (resolved_group or resolved_device) and not command:
            if has_control_verb:
                # Save the resolved target as context NOW so the follow-up
                # "on" / "off" knows what to control without repeating the name.
                from core.state import set_control_context
                if resolved_device:
                    set_control_context(device=resolved_device, control_type="light")
                    # Also mark as pending so bare "on"/"off" resolves here first
                    return {"action": "PENDING_DEVICE_ACTION", "device": resolved_device}
                elif resolved_group:
                    set_control_context(group=resolved_group, control_type="light")
                    return {"action": "CHAT_LOCAL", "response": "What should I do with those lights — turn them on, off, or check status?"}
            # No control verb → treat as general conversation
            return {"action": "CHAT", "message": text}

        # Pronouns
        if re.search(r"\b(it|them|all of them|all of em|those)\b|ito ff", text_lower):
            if not command:
                if has_control_verb:
                    return {"action": "CHAT_LOCAL", "response": "What should I do with the lights — turn them on, off, or check status?"}
                return {"action": "CHAT", "message": text}
            
            if re.search(r"\b(them|all of them|all of em|those)\b", text_lower) or delay > 0:
                group = context.get("group") or get_all_lights()
                if not group:
                    return {"action": "CHAT_LOCAL", "response": "Which devices do you mean?"}
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
            group = context.get("group") or get_all_devices()
            return {"action": "BATCH_DEVICE_COMMAND", "devices": group, "command": command, "delay": delay}
                
        # Local memory handling
        if text_lower in ["show memory", "list memory"]:
            return {"action": "LIST_MEMORY"}
            
        if text_lower in ["clear chat", "reset chat"]:
            return {"action": "CLEAR_CONVERSATION"}
            
        if text_lower in ["clear queue", "cancel queue", "empty queue"]:
            return {"action": "CLEAR_QUEUE"}
            
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

        # Developer Mode Tasks
        DEV_PHRASES = [
            "add a feature", "fix your code", "make yourself able to", "create a new scene",
            "add buzzer support", "change your behavior", "edit your code", "write the esp32 code",
            "make the lights dance differently", "make yourself control", "add a random pulse scene",
            "fix your dance mode", "write esp32 code", "change your input system", "add a command",
            "change your code"
        ]
        if any(text_lower.startswith(p) or p in text_lower for p in DEV_PHRASES):
            return {"action": "DEVELOPER_TASK", "task": text}

        # Autonomous Tasks
        AUTO_PHRASES = [
            "figure it out", "do whatever it takes", "make a script to",
            "write a python script", "scrape", "open instagram and",
            "find a way to", "download and install"
        ]
        if any(p in text_lower for p in AUTO_PHRASES):
            return {"action": "AUTONOMOUS_TASK", "task": text}

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
