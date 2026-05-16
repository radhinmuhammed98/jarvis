import logging
import os
import requests

logger = logging.getLogger(__name__)


def send_multiple_commands(devices: list, command: str, delay: int = 0) -> dict:
    """Send a command to multiple devices sequentially, tracking success/failures."""
    import time
    success = []
    failed = []
    
    for dev in devices:
        res = _send_single_command(dev, command)
        
        # Check if error string was returned
        if any(res.startswith(err) for err in ["Error", "Timeout", "Connection failed", "I don't know"]):
            failed.append(dev)
        else:
            success.append(dev)
            
        if delay > 0 and dev != devices[-1]:
            time.sleep(delay)
            
    return {"success": success, "failed": failed}

def send_esp_command(device: str, command: str) -> str:
    """Send an HTTP command to the ESP32 and return the response text."""
    import os
    base_url = os.getenv("ESP32_BASE_URL", "").rstrip("/")
    if not base_url:
        return "ESP32 base URL is not configured. Set ESP32_BASE_URL in your .env file."

    # Split multiple devices (e.g. "red1,blue")
    devices = [d.strip() for d in device.split(",")]
    
    # Handle "sequence" command entirely in Python
    if "sequence" in devices:
        return send_multiple_commands(["red1", "red2", "blue"], command, delay=1)

    return send_multiple_commands(devices, command, delay=0)

def _send_single_command(device: str, command: str) -> str:
    """Internal helper to send a command to a single strictly valid device ID."""
    from core.device_memory import get_device
    from core.device_state import set_device_state
    import os
    
    base_url = os.getenv("ESP32_BASE_URL", "").rstrip("/")
    if not base_url:
        return "ESP32 base URL is not configured. Check your .env file."
    
    # Check for dynamic pin requests (e.g. "pin_12")
    if device.startswith("pin_"):
        pin_num = device.split("_")[1]
        try:
            url = f"{base_url}/{command}?p={pin_num}"
            import requests
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.text.strip()
        except Exception as e:
            return f"Error on pin {pin_num}."

    # Must be an exact match in memory (except for 'all' virtual group)
    if device == "all":
        endpoint = "all"
    else:
        device_info = get_device(device)
        if not device_info:
            return f"I don't know that device yet. Teach me its name and endpoint first."
        endpoint = device_info.get("endpoint")

    try:
        import requests
        import logging
        logger = logging.getLogger(__name__)
        if command == "status":
            url = f"{base_url}/status"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            try:
                data = response.json()
                if endpoint == "all":
                    return f"Status: Red1 is {data.get('red1', 'unknown')}, Red2 is {data.get('red2', 'unknown')}, Blue is {data.get('blue', 'unknown')}."
                else:
                    return f"{device} is {data.get(endpoint, 'unknown')}."
            except Exception:
                return response.text.strip()
        else:
            url = f"{base_url}/{endpoint}/{command}"
            response = requests.post(url, timeout=5)
            response.raise_for_status()

            # Safely update device state on success
            set_device_state(device, command)

            # Record as last-controlled for troubleshooting
            try:
                from core.control_context import set_last_controlled
                if device != "all":
                    set_last_controlled(device, command)
            except Exception:
                pass

            # ── Post-command verification via /status ─────────────────────
            if device != "all":
                try:
                    verify_url = f"{base_url}/status"
                    v_resp = requests.get(verify_url, timeout=3)
                    if v_resp.ok:
                        status_data = v_resp.json()
                        actual_state = status_data.get(endpoint)
                        if actual_state is not None and actual_state != command:
                            return (
                                f"I sent the command, but {device} still reports "
                                f"{actual_state} instead of {command}."
                            )
                except Exception:
                    pass  # If status check fails, trust the POST succeeded

            res_text = response.text.strip()
            return res_text or f"{device} is {command}."

    except requests.exceptions.Timeout:
        return f"Timeout for {device}."
    except requests.exceptions.ConnectionError:
        return f"Connection failed for {device}."
    except Exception as e:
        logger.error(f"ESP32 error for {device}: {e}")
        return f"Error for {device}."

def get_esp_status() -> dict:
    """Fetch the full status JSON from the ESP32 and update local state."""
    import os
    import requests
    from core.device_state import set_device_state
    
    base_url = os.getenv("ESP32_BASE_URL", "").rstrip("/")
    if not base_url:
        return {}
        
    try:
        response = requests.get(f"{base_url}/status", timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Sync state
        for endpoint, state in data.items():
            # In our setup, device_id matches endpoint for lights
            set_device_state(endpoint, state)
            
        return data
    except Exception as e:
        logger.error(f"Failed to fetch ESP32 status: {e}")
        return {}
