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
            "DEVICE_STATUS_QUERY":  self.handle_device_status_query,
            "SCENE_COMMAND":        self.handle_scene_command,
            "CONTROL_LAST_TARGET":  self.handle_control_last_target,
            "START_SCENE":          self.handle_start_scene,
            "STOP_SCENE":           self.handle_stop_scene,
            "SCENE_SPEED":          self.handle_scene_speed,
            "SCENE_PATTERN":        self.handle_scene_pattern,
            "SCENE_NEXT_PATTERN":   self.handle_scene_next_pattern,
            "SCENE_DURATION":       self.handle_scene_duration,
            "REPEAT_LAST_ACTION":   self.handle_repeat_last_action,
            "SCENE_STATUS":         self.handle_scene_status,
            "SCENE_EXPLAIN":        self.handle_scene_explain,
            "CHOOSE_DEVICE":        self.handle_choose_device,
            "ADD_DEVICE": self.handle_add_device,
            "LIST_DEVICES": self.handle_list_devices,
            "DELETE_DEVICE": self.handle_delete_device,
            "TEST_DEVICES": self.handle_test_devices,
            "ASSIGN_PIN": self.handle_assign_pin,
            "PENDING_DEVICE_ACTION": self.handle_pending_device_action,
            "VERIFY_LAST_DEVICE": self.handle_verify_last_device,
            "CHAT": self.handle_chat,
            "CHAT_LOCAL": self.handle_chat_local,
            "DEVELOPER_TASK": self.handle_developer_task,
            "AUTONOMOUS_TASK": self.handle_autonomous_task,
            "FLASH_FIRMWARE": self.handle_flash_firmware,
            "EXECUTE_SKILL": self.handle_execute_skill,
            "SCHEDULE_TASK": self.handle_schedule_task,
            "REMEMBER": self.handle_remember,
            "RECALL": self.handle_recall,
            "FORGET": self.handle_forget,
            "LIST_MEMORY": self.handle_list_memory,
            "CLEAR_CONVERSATION": self.handle_clear_conversation,
            "CLEAR_MEMORY": self.handle_clear_memory,
            "SET_LISTENING": self.handle_set_listening,
            "RECALL_USER_MESSAGE": self.handle_recall_user_message,
            "LIST_USER_MESSAGES": self.handle_list_user_messages,
            "CLEAR_QUEUE": self.handle_clear_queue,
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
            response = handler(intent_data)

            # Save meaningful actions for the "again" command
            self._save_repeatable_action(action, intent_data, response)
            
            return response
        except Exception as e:
            logger.error(f"Error executing action {action}: {e}")
            return f"An error occurred while executing {action}."

    def _save_repeatable_action(self, action: str, intent_data: dict, response: str):
        """Persist successful actions so they can be repeated with 'again'."""
        # Don't save "again" itself or errors
        if action in ["REPEAT_LAST_ACTION", "CHAT", "UNKNOWN"]:
            return
        if any(err in response for err in ["Error", "Timeout", "Connection failed", "I don't know"]):
            return

        from core.control_context import set_last_action
        
        action_map = {
            "ESP32_COMMAND":        "device_command",
            "CONTROL_LAST_TARGET":  "device_command",
            "BATCH_DEVICE_COMMAND": "batch_command",
            "START_SCENE":          "scene_command",
            "SCENE_PATTERN":        "scene_command",
            "SCENE_NEXT_PATTERN":   "scene_command",
            "DEVICE_STATUS_QUERY":  "status_query"
        }

        if action in action_map:
            set_last_action(action_map[action], intent_data)

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
        from modules.esp32.esp_client import _send_single_command
        from core.state import set_control_context
        device  = intent_data.get("device", "device")
        command = intent_data.get("command", "command")
        logger.info(f"ESP32 command: {command} -> {device}")

        # Clear pending device if this call is consuming it
        if intent_data.get("_clear_pending"):
            from core.control_context import clear_pending_device
            clear_pending_device()

        res = _send_single_command(device, command)
        if not any(res.startswith(err) for err in ["Error", "Timeout", "Connection failed", "I don't know"]):
            if device != "device":
                set_control_context(device=device, control_type="light", command=command)
        
        return res

    def handle_chat(self, intent_data: dict) -> str:
        from core.ai_chat import chat_with_ai
        from core.semantic_memory import add_memory

        message = intent_data.get("message", "")
        if not message:
            return "I'm listening. How can I help?"

        response = chat_with_ai(message)

        # Save interesting conversation exchanges to long-term memory
        # We only save if the message is substantial enough to be a memory
        if len(message) > 15:
            add_memory(f"User said: '{message}'. Jarvis replied: '{response}'", category="conversation")

        return response

    def handle_chat_local(self, intent_data: dict) -> str:
        return intent_data.get("response", "I understood you.")

    def handle_pending_device_action(self, intent_data: dict) -> str:
        """Device identified but no command yet — save as pending and ask."""
        from core.control_context import set_pending_device
        from core.device_memory import get_device
        device = intent_data.get("device", "")
        if not device:
            return "Which device should I control?"
        set_pending_device(device)
        dev_info = get_device(device)
        name = dev_info.get("display_name", device).capitalize() if dev_info else device.capitalize()
        return f"Should I turn {name} on or off?"

    def handle_verify_last_device(self, intent_data: dict) -> str:
        """Check the real ESP32 state of the last controlled device."""
        from core.control_context import get_last_controlled
        from modules.esp32.esp_client import get_esp_status
        from core.device_memory import get_device

        device, command = get_last_controlled()
        if not device:
            return "Which device is not working? I don't have a recent command to verify."

        status_data = get_esp_status()
        dev_info = get_device(device)
        name = dev_info.get("display_name", device).capitalize() if dev_info else device.capitalize()
        endpoint = dev_info.get("endpoint", device) if dev_info else device

        if not status_data:
            return f"I couldn't reach the ESP32 to verify {name}."

        actual = status_data.get(endpoint)
        if actual is None:
            return f"I couldn't find {name} in the ESP32 status response."

        if actual == command:
            return (
                f"ESP32 confirms {name} is {actual}. "
                f"If the physical device is not responding, check wiring or active-low logic."
            )
        else:
            # PROACTIVE FIX: Try re-sending the command once
            logger.info(f"Verification failed for {name}. Retrying {command}...")
            retry_res = self.handle_esp32_command({"device": device, "command": command})
            return (
                f"ESP32 said {name} was {actual}, so I tried sending '{command}' again. "
                f"Result: {retry_res}"
            )



    def handle_remember(self, intent_data: dict) -> str:
        from core.memory import remember, normalize_key, denormalize_key
        from core.semantic_memory import add_memory

        key = intent_data.get("key", "")
        value = intent_data.get("value", "")
        category = intent_data.get("category", "general")
        
        if not key or not value:
            return "I need both a key and a value to remember something."
            
        # Save to exact-match memory (SQLite)
        success = remember(key, value, category)

        # Also save to semantic memory (ChromaDB)
        add_memory(f"Fact: {key} is {value}", category="fact")

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
        from core.device_memory import get_all_lights
        from core.state import set_control_context
        
        devices = intent_data.get("devices", [])
        command = intent_data.get("command", "on")
        delay = intent_data.get("delay", 0)
        
        if not devices:
            return "I need a list of devices to run a batch command."
            
        if devices == "ALL_LIGHTS" or (isinstance(devices, list) and "ALL_LIGHTS" in devices):
            devices = get_all_lights()
            
        if delay == 0 and set(devices) == set(get_all_lights()):
            from modules.esp32.esp_client import _send_single_command
            res_text = _send_single_command("all", command)
            if not any(res_text.startswith(err) for err in ["Error", "Timeout", "Connection failed", "I don't know"]):
                set_control_context(group=devices, control_type="light", command=command)
                return f"All lights turned {command}."
            else:
                return "I couldn't control any of those devices."
            
        res = send_multiple_commands(devices, command, delay)
        
        success = res.get("success", [])
        failed = res.get("failed", [])
        
        # Only set context if at least one succeeded
        if success:
            set_control_context(group=success, control_type="light" if devices == get_all_lights() else None)
        
        if not success:
            return "I couldn't control any of those devices."
            
        if failed:
            failed_names = [d.replace("_", " ") for d in failed]
            return f"I couldn't control: {', '.join(failed_names)}."
            
        if delay > 0:
            return f"I turned the devices {command} one by one."
        elif devices == get_all_lights():
            return f"All lights turned {command}."
            
        friendly_success = [d.replace("_", " ") for d in success]
        return f"Successfully turned {command}: {', '.join(friendly_success)}."

    def handle_device_status_query(self, intent_data: dict) -> str:
        from modules.esp32.esp_client import get_esp_status
        from core.device_memory import get_device
        
        state = intent_data.get("state", "on")
        device_type = intent_data.get("device_type", None)
        
        status_data = get_esp_status()
        if not status_data:
            return "I couldn't reach the devices to check their current status."
            
        matching_endpoints = [ep for ep, ep_state in status_data.items() if ep_state == state]
        
        if not matching_endpoints:
            return f"No devices are currently {state}."
            
        # Map endpoints to friendly display names
        friendly_names = []
        for ep in matching_endpoints:
            device_info = get_device(ep)
            if device_info:
                friendly_names.append(device_info.get("display_name", ep))
            else:
                friendly_names.append(ep)
                
        if len(friendly_names) == 1:
            return f"{friendly_names[0].capitalize()} is {state}."
        elif len(friendly_names) == 2:
            return f"{friendly_names[0].capitalize()} and {friendly_names[1]} are {state}."
        else:
            names_str = ", ".join(friendly_names[:-1]) + f", and {friendly_names[-1]}"
            # Capitalize only the first letter of the whole string
            names_str = names_str[0].upper() + names_str[1:]
            return f"{names_str} are {state}."

    def handle_scene_command(self, intent_data: dict) -> str:
        from modules.esp32.esp_client import send_multiple_commands, _send_single_command
        from core.device_memory import get_all_lights
        from core.state import set_control_context, get_control_context
        from core.scenes import run_dance_scene

        scene = intent_data.get("scene")
        target = intent_data.get("target", "")

        # ── Dance scenes ─────────────────────────────────────────────────
        if scene == "dance":
            if target == "ALL_LIGHTS":
                devices = get_all_lights()
                if not devices:
                    return "I don't have any lights in my memory."
                set_control_context(group=devices, control_type="light", command="dance")
                return run_dance_scene(devices)

            elif target == "LAST_TARGET":
                ctx = get_control_context()
                devices = ctx.get("group") or ([ctx["device"]] if ctx.get("device") else None)
                if not devices:
                    return "I don't know what to dance yet. Control a device once first."
                return run_dance_scene(devices)

        # ── Colour-only scenes ────────────────────────────────────────────
        if scene == "blue_only":
            all_lights = get_all_lights()
            send_multiple_commands(all_lights, "off")
            _send_single_command("blue", "on")
            set_control_context(device="blue", control_type="light", command="on")
            return "Only the blue light is on."

        if scene == "red_only":
            _send_single_command("blue", "off")
            send_multiple_commands(["red1", "red2"], "on")
            set_control_context(group=["red1", "red2"], control_type="light", command="on")
            return "Only the red lights are on."

        return "Unknown scene."

    def handle_control_last_target(self, intent_data: dict) -> str:
        """
        Apply a command (on/off) to the last known device or group.
        Falls back to 'no previous target' message if nothing is stored.
        """
        from modules.esp32.esp_client import send_multiple_commands, _send_single_command
        from core.state import get_control_context, set_control_context
        from core.device_memory import get_device

        command = intent_data.get("command", "on")
        ctx = get_control_context()

        group  = ctx.get("group")
        device = ctx.get("device")

        if not group and not device:
            return "I don't know what to control yet. Control a device once first."

        if group:
            # Use the fast /all/on endpoint if it matches the full light set
            from core.device_memory import get_all_lights
            if set(group) == set(get_all_lights()):
                res = _send_single_command("all", command)
            else:
                res_data = send_multiple_commands(group, command)
                failed = res_data.get("failed", [])
                if len(failed) == len(group):
                    return "I couldn't control any of those devices."
                if failed:
                    return f"I couldn't control: {', '.join(failed)}."
                res = "ok"

            err_prefixes = ("Error", "Timeout", "Connection failed", "I don't know")
            if not isinstance(res, str) or not any(res.startswith(e) for e in err_prefixes):
                set_control_context(group=group, control_type="light", command=command)
                return f"I turned them {command}."
            return "I couldn't control those devices."

        else:
            # Single device
            res = _send_single_command(device, command)
            err_prefixes = ("Error", "Timeout", "Connection failed", "I don't know")
            if not any(res.startswith(e) for e in err_prefixes):
                set_control_context(device=device, control_type="light", command=command)
                dev_info = get_device(device)
                name = dev_info.get("display_name", device) if dev_info else device
                return f"{name.capitalize()} turned {command}."
            return f"I couldn't control {device}."

    # ── Background scene handlers ───────────────────────────────────────────

    # ── Scene handlers (all call scene_runtime directly, never AI) ────────────

    def handle_start_scene(self, intent_data: dict) -> str:
        from core.scene_runtime import start_scene
        from core.device_memory import get_all_lights
        from core.state import get_control_context, set_control_context
        from core.control_context import set_context

        target  = intent_data.get("target", "ALL_LIGHTS")
        pattern = intent_data.get("pattern", "chase")
        speed   = intent_data.get("speed", 0.25)

        if target == "ALL_LIGHTS":
            devices = get_all_lights()
        elif target == "LAST_TARGET":
            ctx = get_control_context()
            devices = ctx.get("group") or ([ctx["device"]] if ctx.get("device") else None)
        else:
            devices = None

        if not devices:
            return "I don't know what to dance yet. Control a device once first."

        set_control_context(group=devices, control_type="light")
        set_context("last_scene_trigger", "direct")
        return start_scene(devices=devices, pattern=pattern, speed=speed)

    def handle_stop_scene(self, intent_data: dict) -> str:
        from core.scene_runtime import stop_scene
        return stop_scene()

    def handle_scene_speed(self, intent_data: dict) -> str:
        from core.scene_runtime import speed_up, slow_down, is_scene_running
        direction = intent_data.get("direction", "faster")
        if not is_scene_running():
            return "No light scene is running."
        if direction == "faster":
            return speed_up()
        return slow_down()

    def handle_scene_pattern(self, intent_data: dict) -> str:
        from core.scene_runtime import change_pattern, is_scene_running, speed_up, slow_down
        pattern = intent_data.get("pattern", "chase")
        
        if not is_scene_running():
            # Auto-start scene if a specific pattern is requested while off
            logger.info(f"Auto-starting scene with pattern {pattern}")
            return self.handle_start_scene({"target": "ALL_LIGHTS", "pattern": pattern})
        
        res = change_pattern(pattern)
        
        speed_dir = intent_data.get("speed_direction")
        if speed_dir == "faster":
            speed_up()
            res += " Speed increased."
        elif speed_dir == "slower":
            slow_down()
            res += " Speed decreased."
            
        return res

    def handle_scene_next_pattern(self, intent_data: dict) -> str:
        from core.scene_runtime import next_pattern, is_scene_running
        if not is_scene_running():
            return "No light scene is running. Say 'dance lights' to start one."
        return next_pattern()

    def handle_scene_duration(self, intent_data: dict) -> str:
        from core.scene_runtime import set_duration, is_scene_running
        seconds = intent_data.get("seconds", 5)
        if not is_scene_running():
            return "No light scene is running."
        return set_duration(float(seconds))

    def handle_repeat_last_action(self, intent_data: dict) -> str:
        """Repeat exactly the last successful meaningful action (device, batch, scene, or status)."""
        from core.control_context import get_last_action, set_context
        
        action_type, last_intent = get_last_action()
        
        if not action_type or not last_intent:
            return "What should I repeat? I don't have a previous action recorded yet."

        logger.info(f"Repeating last action: {action_type} -> {last_intent.get('action')}")

        if action_type == "device_command":
            return self.handle_esp32_command(last_intent)
        elif action_type == "batch_command":
            return self.handle_batch_device_command(last_intent)
        elif action_type == "scene_command":
            # If it was a START_SCENE, just run it again
            if last_intent.get("action") == "START_SCENE":
                res = self.handle_start_scene(last_intent)
                set_context("last_scene_trigger", "repeat")
                return res
            # If it was a pattern change while running, we can't easily "repeat" 
            # if stopped, but we can call handle_scene_pattern
            res = self.handlers.get(last_intent["action"])(last_intent)
            set_context("last_scene_trigger", "repeat")
            return res
        elif action_type == "status_query":
            return self.handle_device_status_query(last_intent)
        
        return "I don't know how to repeat that type of action."

    def handle_scene_status(self, intent_data: dict) -> str:
        from core.scene_runtime import get_scene_status
        return get_scene_status()

    def handle_scene_explain(self, intent_data: dict) -> str:
        """Explain why the current scene is running."""
        from core.scene_runtime import is_scene_running, stop_scene
        from core.control_context import get_context

        if not is_scene_running():
            return "No light scene is running right now."

        trigger = get_context("last_scene_trigger")
        if trigger == "repeat":
            stop_scene()
            return "I repeated the last saved scene, but that was probably wrong. I'll stop it."
        elif trigger == "direct":
            return "You asked me to start the light scene."
        
        return "I'm not sure how this scene started, but I can stop it if you want."

    def handle_choose_device(self, intent_data: dict) -> str:
        """Autonomously choose a light to turn on from registered devices."""
        from core.device_memory import get_all_lights, get_device
        from modules.esp32.esp_client import get_esp_status

        lights = get_all_lights()
        if not lights:
            return "I don't have any registered lights to choose from."

        status_data = get_esp_status()
        off_devices = []
        on_devices = []

        for lid in lights:
            dev = get_device(lid)
            if not dev: continue
            
            endpoint = dev.get("endpoint", "").strip("/")
            state = status_data.get(endpoint)
            
            if state == "off":
                off_devices.append(lid)
            elif state == "on":
                on_devices.append(lid)

        # Logic: 
        # 1. Prefer off devices
        # 2. If all off, default red1
        # 3. If all on, default blue
        
        chosen_id = None
        if off_devices:
            # If all are off, pick red1 if available, otherwise just the first off one
            if len(off_devices) == len(lights) and "red1" in off_devices:
                chosen_id = "red1"
            else:
                chosen_id = off_devices[0]
        else:
            # All are on, default to blue
            if "blue" in on_devices:
                chosen_id = "blue"
            else:
                chosen_id = on_devices[0]

        if not chosen_id:
            return "I couldn't decide which light to choose."

        dev_info = get_device(chosen_id)
        name = dev_info.get("display_name") or chosen_id
        
        # Execute the command
        res = self.handle_esp32_command({"device": chosen_id, "command": "on"})
        
        if "turned on" in res:
             return f"I chose {name} and turned it on."
        return f"I chose {name}, but I couldn't turn it on: {res}"



    def handle_add_device(self, intent_data: dict) -> str:
        from core.device_memory import add_device
        device_id = intent_data.get("device_id")
        display_name = intent_data.get("display_name")
        dtype = intent_data.get("type", "unknown")
        endpoint = intent_data.get("endpoint")
        color = intent_data.get("color")
        aliases = intent_data.get("aliases", [])
        
        if not device_id or not endpoint:
            return "I need a device ID and an endpoint to remember a new device."
            
        success = add_device(device_id, display_name, dtype, endpoint, color, aliases)
        if success:
            return f"I have memorized the device {display_name or device_id}."
        return f"I couldn't add {device_id}. It might already exist."

    def handle_list_devices(self, intent_data: dict) -> str:
        from core.device_memory import list_devices
        devices = list_devices()
        if not devices:
            return "I don't have any devices in my memory right now."
        names = [d.get("display_name") or d.get("device_id") for d in devices]
        return f"I know these devices: {', '.join(names)}."

    def handle_delete_device(self, intent_data: dict) -> str:
        from core.device_memory import delete_device
        device_id = intent_data.get("device_id")
        if not device_id:
            return "Which device should I forget?"
        
        success = delete_device(device_id)
        if success:
            return f"I have forgotten {device_id}."
        return f"I couldn't find {device_id} in my memory."

    def handle_test_devices(self, intent_data: dict) -> str:
        from core.device_memory import list_devices
        from modules.esp32.esp_client import _send_single_command
        
        devices = list_devices()
        if not devices:
            return "No devices in memory to test."
            
        results = []
        for d in devices:
            did = d["device_id"]
            res = _send_single_command(did, "status")
            if any(res.startswith(err) for err in ["Error", "Timeout", "Connection failed", "I don't know"]):
                results.append(f"{did}: FAILED")
            else:
                results.append(f"{did}: OK")
                
        return f"Device Test Results: {', '.join(results)}"

    def handle_clear_queue(self, intent_data: dict) -> str:
        from core.input_queue import clear_input_queue
        count = clear_input_queue()
        if count:
            return f"I cleared {count} pending input{'s' if count > 1 else ''}."
        return "I cleared pending inputs."

    def handle_exit(self, intent_data: dict) -> str:
        return "ACTION_EXIT"

    def handle_developer_task(self, intent_data: dict) -> str:
        from core.developer_agent import run_developer_task
        task = intent_data.get("task", "")
        if not task:
            return "What would you like me to develop?"
        
        # This might take a while, so we could potentially return a preliminary message
        # But for now, we block and return the result.
        return run_developer_task(task)

    def handle_autonomous_task(self, intent_data: dict) -> str:
        from core.autonomous_agent import execute_autonomous_task
        task = intent_data.get("task", "")
        if not task:
            return "What autonomous task would you like me to perform?"
        return execute_autonomous_task(task)

    def handle_flash_firmware(self, intent_data: dict) -> str:
        from core.firmware_agent import flash_firmware
        request = intent_data.get("request") or intent_data.get("task", "")
        if not request:
            return "What would you like the ESP32 to do?"
        return flash_firmware(request)

    def handle_execute_skill(self, intent_data: dict) -> str:
        from core.skill_manager import execute_skill
        skill_name = intent_data.get("skill_name")
        args = intent_data.get("args", "")
        if not skill_name:
            return "Which skill should I execute?"
        return execute_skill(skill_name, args)

    def handle_schedule_task(self, intent_data: dict) -> str:
        from core.scheduler import schedule_task
        interval = intent_data.get("interval", 1)
        unit = intent_data.get("unit", "minutes")
        run_once = intent_data.get("run_once", False)
        nested_intent = intent_data.get("nested_intent")

        if not nested_intent:
            return "I need to know what task you want me to schedule."

        def job_wrapper():
            # Run the executor on the nested intent
            logger.info(f"Running scheduled job: {nested_intent.get('action')}")
            try:
                self.execute(nested_intent)
            except Exception as e:
                logger.error(f"Scheduled job failed: {e}")

        success = schedule_task(job_wrapper, interval, unit, run_once)

        if success:
            mode = "once" if run_once else "recurring"
            return f"Scheduled task: {nested_intent.get('action')} every {interval} {unit} ({mode})."
        return "I couldn't understand the scheduling parameters."

    def handle_unknown(self, intent_data: dict) -> str:
        return "I'm not sure how to help with that yet."
