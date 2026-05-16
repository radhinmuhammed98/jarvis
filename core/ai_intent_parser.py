import os
import json
import logging
import requests

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are ONLY an intent parser for a Jarvis assistant.
Return ONLY valid JSON.
Never answer as yourself.
Never reveal model names like Nemotron.
Never make conversation.
Your job is to classify the user input into an action.

Important:
- Casual messages like "hi", "hey", "hyy", "hello", "haha", "lol", "ok", "what", "whats ur name", "ur not intelligent" must return CHAT.
- Questions like "what is nemotron", "nemotron means?", "explain black holes" must return CHAT, not SEARCH_WEB.
- SEARCH_WEB should only be used when the user clearly asks to search/google/look up something.
- OPEN_APP should only be used when the user clearly asks to open/launch/start an app or website.
- REMEMBER should be used when the user asks Jarvis to remember, store, or save a fact. The key should be a simple noun phrase (e.g., "my name", "the code").
- RECALL should be used when the user asks what a previously stored fact is.
- FORGET should be used when the user asks to delete a memory.
- LIST_MEMORY should be used when the user asks to show or list all memories.
- If unsure, return CHAT.

Important for Device Control:
- To control a single device, use: {"action": "ESP32_COMMAND", "device": "light", "command": "on"}
- To control multiple devices or "ALL_LIGHTS", use: {"action": "BATCH_DEVICE_COMMAND", "devices": ["light", "blue_light"], "command": "on", "delay": 0}
- To execute a sequence (one-by-one with gap), use: {"action": "BATCH_DEVICE_COMMAND", "devices": "ALL_LIGHTS", "command": "on", "delay": 1}
- NEVER output raw user phrases as device names. ONLY use valid device IDs (e.g., "light", "blue_light", "red1", "red2", "fan", "ALL_LIGHTS") or "pin_X".
- To control a specific GPIO pin, use: "device": "pin_X" (e.g., "pin_12").
- To assign a name to a pin (e.g., "pin 4 is fan"), use: {"action": "ASSIGN_PIN", "device_name": "fan", "pin": 4}.
- Use "command": "on", "off", or "status".

Allowed actions:
OPEN_APP, SEARCH_WEB, GET_TIME, SYSTEM_INFO, ESP32_COMMAND, BATCH_DEVICE_COMMAND, ASSIGN_PIN, EXIT, CHAT, REMEMBER, RECALL, FORGET, LIST_MEMORY, CLEAR_CONVERSATION.

Output examples:
{"action":"BATCH_DEVICE_COMMAND","devices":"ALL_LIGHTS","command":"on","delay":0}
{"action":"BATCH_DEVICE_COMMAND","devices":["red1","blue"],"command":"off","delay":1}
{"action":"ASSIGN_PIN","device_name":"fan","pin":4}
{"action":"CHAT","message":"hyy"}
{"action":"CHAT","message":"haha"}
{"action":"CHAT","message":"whats ur name"}
{"action":"CHAT","message":"nemotron means?"}
{"action":"OPEN_APP","target":"browser"}
{"action":"SEARCH_WEB","query":"how to install flask"}
{"action":"REMEMBER","key":"my name","value":"Radhin"}
{"action":"RECALL","key":"my name"}
{"action":"FORGET","key":"my name"}
{"action":"LIST_MEMORY"}

Return only JSON. No markdown. No explanation.
"""

def parse_with_ai(user_input: str) -> dict:
    """
    Sends the user input to the configured AI provider to parse the intent into JSON.
    """
    logger.info(f"Jarvis is thinking (Intent Parsing)...")
    
    from core.ai_provider import call_ai
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input}
    ]

    try:
        ai_message = call_ai(messages, temperature=0.0)
        
        # 1. Strip whitespace
        ai_message = ai_message.strip()
        
        # 2. Remove ```json and ``` code fences if present
        if ai_message.startswith("```json"):
            ai_message = ai_message[7:]
        elif ai_message.startswith("```"):
            ai_message = ai_message[3:]
            
        if ai_message.endswith("```"):
            ai_message = ai_message[:-3]
            
        ai_message = ai_message.strip()
        
        # 3. Try json.loads()
        try:
            parsed_json = json.loads(ai_message)
        except json.JSONDecodeError as e:
            logger.debug(f"AI returned invalid JSON: {e}")
            return {"action": "CHAT", "message": user_input}
            
        # 5. If parsed JSON is not a dict
        if not isinstance(parsed_json, dict):
            logger.debug("AI returned JSON that is not a dictionary.")
            return {"action": "CHAT", "message": user_input}
        
        # 6. If "action" key is missing
        if "action" not in parsed_json:
            logger.debug("AI returned JSON without an 'action' key.")
            return {"action": "CHAT", "message": user_input}
            
        # 7. If action is not in allowed actions
        allowed_actions = ["OPEN_APP", "SEARCH_WEB", "GET_TIME", "SYSTEM_INFO", "ESP32_COMMAND", "BATCH_DEVICE_COMMAND", "ASSIGN_PIN", "EXIT", "CHAT", "REMEMBER", "RECALL", "FORGET", "LIST_MEMORY", "CLEAR_CONVERSATION"]
        if parsed_json["action"] not in allowed_actions:
            logger.debug(f"AI returned unknown action: {parsed_json['action']}")
            return {"action": "CHAT", "message": user_input}
            
        return parsed_json
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {"action": "CHAT", "message": user_input}
    except Exception as e:
        logger.error(f"Unexpected error during AI parsing: {e}")
        return {"action": "CHAT", "message": user_input}


