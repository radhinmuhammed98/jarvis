import logging
import subprocess
import platform
import shutil
import urllib.parse
from datetime import datetime

logger = logging.getLogger(__name__)

class CommandExecutor:
    def __init__(self):
        # Register command handlers
        self.handlers = {
            "OPEN_APP": self.handle_open_app,
            "SEARCH_WEB": self.handle_search_web,
            "GET_TIME": self.handle_get_time,
            "SYSTEM_INFO": self.handle_system_info,
            "ESP32_COMMAND": self.handle_esp32_command,
            "BATCH_DEVICE_COMMAND": self.handle_batch_device_command,
            "DEVICE_STATUS_QUERY": self.handle_device_status_query,
            "SCENE_COMMAND": self.handle_scene_command,
            "ASSIGN_PIN": self.handle_assign_pin,
            "CHAT": self.handle_chat,
            "CHAT_LOCAL": self.handle_chat_local,
            "REMEMBER": self.handle_remember,
            "RECALL": self.handle_recall,
            "FORGET": self.handle_forget,
            "LIST_MEMORY": self.handle_list_memory,
            "CLEAR_CONVERSATION": self.handle_clear_conversation,
            "CLEAR_MEMORY": self.handle_clear_memory,
            "SET_LISTENING": self.handle_set_listening,
            "RECALL_USER_MESSAGE": self.handle_recall_user_message,
            "LIST_USER_MESSAGES": self.handle_list_user_messages,
            "EXIT": self.handle_exit
        }

    def execute(self, intent_data: dict) -> str:
        """
        Executes the action associated with the given intent dictionary.
        """
        action = intent_data.get("action", "CHAT")
        logger.debug(f"Executing action: {action}")
        
        handler = self.handlers.get(action, self.handle_unknown)
        try:
            return handler(intent_data)
        except Exception as e:
            logger.error(f"Error executing action {action}: {e}")
            return f"An error occurred while executing {action}."

    def _open_any_browser(self):
        """Helper function to try opening a web browser in a specific order."""
        browsers = ["google-chrome", "chromium", "chromium-browser", "firefox"]
        for browser in browsers:
            if shutil.which(browser):
                subprocess.Popen([browser], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return browser
        return None

    def handle_open_app(self, intent_data: dict) -> str:
        target = intent_data.get("target", "unknown").lower()
        import webbrowser
        import os
        
        if target == "firefox":
            if shutil.which("firefox"):
                subprocess.Popen(["firefox"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return "Opening Firefox..."
            return "I couldn't find Firefox installed."
            
        elif target in ["chrome", "browser", "web browser"]:
            opened_browser = self._open_any_browser()
            if opened_browser:
                name = opened_browser.replace("-", " ").title()
                return f"Opening {name}..."
            return "I couldn't find a web browser installed."
            
        elif target == "whatsapp":
            webbrowser.open("https://web.whatsapp.com")
            return "Opening WhatsApp..."
            
        elif target == "youtube":
            webbrowser.open("https://youtube.com")
            return "Opening YouTube..."
            
        elif target == "google":
            webbrowser.open("https://google.com")
            return "Opening Google..."
            
        elif target == "terminal":
            terminals = ["x-terminal-emulator", "gnome-terminal", "konsole", "xfce4-terminal"]
            for term in terminals:
                if shutil.which(term):
                    subprocess.Popen([term], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return "Opening terminal..."
            return "I couldn't find a terminal installed."
            
        elif target == "files":
            if shutil.which("xdg-open"):
                home_dir = os.path.expanduser("~")
                subprocess.Popen(["xdg-open", home_dir], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return "Opening files..."
            return "I couldn't find xdg-open installed."
            
        elif target in ["vscode", "code"]:
            if shutil.which("code"):
                subprocess.Popen(["code"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return "Opening Visual Studio Code..."
            return "I couldn't find Visual Studio Code installed."
            
        return f"I don't know how to open {target}."

    def handle_search_web(self, intent_data: dict) -> str:
        import webbrowser
        query = intent_data.get("query", "")
        if not query:
            return "What would you like me to search for?"
        
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.google.com/search?q={encoded_query}"
        
        try:
            success = webbrowser.open(url)
            if success:
                return f"Searching the web for: {query}"
            else:
                raise Exception("webbrowser.open returned False")
        except Exception as e:
            logger.warning(f"webbrowser failed ({e}), falling back to xdg-open")
            try:
                # Fallback to subprocess
                subprocess.run(["xdg-open", url], check=True)
                return f"Searching the web for: {query}"
            except Exception as subprocess_error:
                error_msg = f"Failed to search web. Error: {subprocess_error}"
                logger.error(error_msg)
                return error_msg

    def handle_get_time(self, intent_data: dict) -> str:
        now = datetime.now().strftime("%I:%M %p")
        return f"The current time is {now}."

    def handle_system_info(self, intent_data: dict) -> str:
        os_info = f"{platform.system()} {platform.release()}"
        arch = platform.machine()
        return f"System is running {os_info} on {arch} architecture."

    def handle_esp32_command(self, intent_data: dict) -> str:
        from modules.esp32.esp_client import send_esp_command
        from core.state import set_control_context
        device = intent_data.get("device", "device")
        command = intent_data.get("command", "command")
        logger.info(f"ESP32 command: {command} -> {device}")
        
        if device != "device":
            set_control_context(device=device, control_type="light")
            
        return send_esp_command(device, command)

    def handle_chat(self, intent_data: dict) -> str:
        from core.ai_chat import chat_with_ai
        message = intent_data.get("message", "")
        if not message:
            return "I'm listening. How can I help?"
        return chat_with_ai(message)

    def handle_chat_local(self, intent_data: dict) -> str:
        return intent_data.get("response", "I understood you.")

    def handle_remember(self, intent_data: dict) -> str:
        from core.memory import remember, normalize_key, denormalize_key
        key = intent_data.get("key", "")
        value = intent_data.get("value", "")
        category = intent_data.get("category", "general")
        
        if not key or not value:
            return "I need both a key and a value to remember something."
            
        success = remember(key, value, category)
        if success:
            display_key = denormalize_key(normalize_key(key))
            return f"Got it. I'll remember that {display_key} is {value}."
        return f"Sorry, I couldn't save that memory."

    def handle_recall(self, intent_data: dict) -> str:
        from core.memory import recall, normalize_key, denormalize_key
        key = intent_data.get("key", "")
        
        if not key:
            return "What would you like me to recall?"
            
        value = recall(key)
        display_key = denormalize_key(normalize_key(key))
        if value:
            # Capitalize the first letter for a cleaner natural language response
            key_cap = display_key[0].upper() + display_key[1:] if display_key else display_key
            return f"{key_cap} is {value}."
        return f"I don't have anything in my memory about {display_key}."

    def handle_forget(self, intent_data: dict) -> str:
        from core.memory import forget, normalize_key, denormalize_key
        key = intent_data.get("key", "")
        
        if not key:
            return "What would you like me to forget?"
            
        success = forget(key)
        display_key = denormalize_key(normalize_key(key))
        if success:
            return f"I forgot {display_key}."
        return f"I don't have anything stored for {display_key} anyway."

    def handle_list_memory(self, intent_data: dict) -> str:
        from core.memory import list_memories, denormalize_key
        memories = list_memories()
        
        if not memories:
            return "My memory is currently empty."
            
        response = "Here is what I remember:\n"
        for mem in memories:
            display_key = denormalize_key(mem['key'])
            response += f"- {display_key}: {mem['value']}\n"
        return response.strip()

    def handle_clear_conversation(self, intent_data: dict) -> str:
        from core.conversation import clear_conversation
        clear_conversation()
        return "I cleared this conversation history."

    def handle_clear_memory(self, intent_data: dict) -> str:
        from core.memory import clear_all_memories
        clear_all_memories()
        return "I cleared all saved memories."

    def handle_set_listening(self, intent_data: dict) -> str:
        from core.state import set_listening
        value = intent_data.get("value", True)
        set_listening(value)
        if value:
            return "I'm listening again."
        else:
            return "I'll remain silent."

    def handle_recall_user_message(self, intent_data: dict) -> str:
        from core.conversation import get_nth_user_message
        idx = intent_data.get("index", 1)
        msg = get_nth_user_message(idx)
        
        ordinals = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth"}
        ord_str = ordinals.get(idx, f"{idx}th")
        
        if msg:
            return f"Your {ord_str} message was: {msg}"
        return f"You haven't sent a {ord_str} message yet."

    def handle_list_user_messages(self, intent_data: dict) -> str:
        from core.conversation import get_user_messages
        msgs = get_user_messages()
        
        if not msgs:
            return "You haven't said anything yet."
            
        response = "Here are your messages:\n"
        for i, m in enumerate(msgs):
            response += f"{i+1}. {m}\n"
        return response.strip()

    def handle_assign_pin(self, intent_data: dict) -> str:
        from modules.esp32.device_manager import save_device_mapping
        device_name = intent_data.get("device_name")
        pin = intent_data.get("pin")
        if device_name and pin:
            return save_device_mapping(device_name, pin)
        return "I need both a device name and a pin number to make an assignment."

    def handle_batch_device_command(self, intent_data: dict) -> str:
        from modules.esp32.esp_client import send_multiple_commands
        from core.device_registry import get_all_lights
        from core.state import set_control_context
        
        devices = intent_data.get("devices", [])
        command = intent_data.get("command", "on")
        delay = intent_data.get("delay", 0)
        
        if not devices:
            return "I need a list of devices to run a batch command."
            
        if devices == "ALL_LIGHTS" or (isinstance(devices, list) and "ALL_LIGHTS" in devices):
            devices = get_all_lights()
            set_control_context(group=devices, control_type="light")
        else:
            set_control_context(group=devices)
            
        res = send_multiple_commands(devices, command, delay)
        
        if delay > 0:
            return f"I turned the lights {command} one by one."
        elif devices == get_all_lights():
            return f"All lights turned {command}."
            
        return res

    def handle_device_status_query(self, intent_data: dict) -> str:
        from core.device_state import get_devices_by_state
        state = intent_data.get("state", "on")
        device_type = intent_data.get("device_type", None)
        
        devices = get_devices_by_state(state, device_type)
        if not devices:
            return f"No {device_type + 's' if device_type else 'devices'} are currently marked as {state}."
            
        # Clean up names for response
        friendly_names = [d.replace("_", " ") for d in devices]
        return f"These devices are {state}: {', '.join(friendly_names)}."

    def handle_scene_command(self, intent_data: dict) -> str:
        from modules.esp32.esp_client import send_multiple_commands, _send_single_command
        from core.device_registry import get_all_lights
        from core.state import set_control_context
        
        scene = intent_data.get("scene")
        if scene == "blue_only":
            all_lights = get_all_lights()
            send_multiple_commands(all_lights, "off")
            _send_single_command("blue_light", "on")
            set_control_context(device="blue_light", control_type="light")
            return "Only the blue light is on."
            
        return "Unknown scene."

    def handle_exit(self, intent_data: dict) -> str:
        return "ACTION_EXIT"

    def handle_unknown(self, intent_data: dict) -> str:
        return "I'm not sure how to help with that yet."
