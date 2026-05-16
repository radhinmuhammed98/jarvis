import logging
import os
import requests

logger = logging.getLogger(__name__)

ESP32_BASE_URL = os.getenv("ESP32_BASE_URL", "").rstrip("/")

def send_multiple_commands(devices: list, command: str, delay: int = 0) -> str:
    """Send a command to multiple devices sequentially, with an optional delay."""
    import time
    responses = []
    for dev in devices:
        res = _send_single_command(dev, command)
        responses.append(res)
        if delay > 0:
            time.sleep(delay)
            
    if len(responses) == 1:
        return responses[0]
    return " | ".join(responses)

def send_esp_command(device: str, command: str) -> str:
    """Send an HTTP command to the ESP32 and return the response text."""
    if not ESP32_BASE_URL:
        return "ESP32 base URL is not configured. Set ESP32_BASE_URL in your .env file."

    # Split multiple devices (e.g. "red1,blue")
    devices = [d.strip() for d in device.split(",")]
    
    # Handle "sequence" command entirely in Python
    if "sequence" in devices:
        return send_multiple_commands(["red1", "red2", "blue"], command, delay=1)

    return send_multiple_commands(devices, command, delay=0)

def _send_single_command(device: str, command: str) -> str:
    """Internal helper to send a command to a single strictly valid device ID."""
    from core.device_registry import get_device
    from core.device_state import set_device_state
    
    # Check for dynamic pin requests (e.g. "pin_12")
    if device.startswith("pin_"):
        pin_num = device.split("_")[1]
        try:
            url = f"{ESP32_BASE_URL}/{command}?p={pin_num}"
            import requests
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.text.strip()
        except Exception as e:
            return f"Error on pin {pin_num}."

    # Must be an exact match in registry
    device_info = get_device(device)
    if not device_info:
        return f"I don't know that device yet."
        
    endpoint = device_info.get("endpoint")

    try:
        import requests
        import logging
        logger = logging.getLogger(__name__)
        if command == "status":
            url = f"{ESP32_BASE_URL}/{endpoint}/status"
            response = requests.get(url, timeout=5)
        else:
            url = f"{ESP32_BASE_URL}/{endpoint}/{command}"
            response = requests.post(url, timeout=5)

        response.raise_for_status()
        res_text = response.text.strip()
        
        # Safely update device state on success
        set_device_state(device, command)
        
        return res_text or f"{device} is {command}."

    except requests.exceptions.Timeout:
        return f"Timeout for {device}."
    except requests.exceptions.ConnectionError:
        return f"Connection failed for {device}."
    except Exception as e:
        logger.error(f"ESP32 error for {device}: {e}")
        return f"Error for {device}."
