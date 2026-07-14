import os
import json
import logging
import subprocess
import tempfile
import shutil
from core.ai_provider import call_ai

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Jarvis's Firmware Engineering Agent.
Your job is to generate complete, valid C++ code for an ESP32 microcontroller based on the user's request.
The code should be ready to compile in the Arduino/PlatformIO framework.

IMPORTANT: Output ONLY a JSON object containing the code.
Do not output any markdown or explanatory text outside the JSON block.

JSON Format:
{
  "code": "#include <Arduino.h>\n\nvoid setup() {\n  Serial.begin(115200);\n}\n\nvoid loop() {\n  Serial.println(\"Hello\");\n  delay(1000);\n}"
}
"""

def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        return None

def check_platformio():
    """Checks if platformio (pio) is installed, attempts to install if not."""
    try:
        subprocess.run(["pio", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.info("PlatformIO not found. Attempting to install via pip...")
        try:
            subprocess.run(["pip", "install", "platformio"], check=True)
            return True
        except subprocess.CalledProcessError:
            return False

def flash_firmware(request: str) -> str:
    """Generates ESP32 firmware based on the request and attempts to flash it."""
    logger.info(f"Starting firmware generation for request: {request}")

    if not check_platformio():
        return "I could not find or install PlatformIO (pio), which is required to flash the ESP32."

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Please generate ESP32 firmware for this request: {request}"}
    ]

    try:
        response = call_ai(messages, temperature=0.2)
    except Exception as e:
        logger.error(f"AI call failed for firmware generation: {e}")
        return f"I had trouble thinking about the firmware: {e}"

    action_data = extract_json(response)
    if not action_data or "code" not in action_data:
        return "I failed to generate valid firmware code."

    code = action_data["code"]

    # Create temporary PlatformIO project
    temp_dir = tempfile.mkdtemp(prefix="jarvis_firmware_")
    try:
        # Initialize PlatformIO project
        logger.info(f"Initializing PlatformIO project in {temp_dir}")
        init_res = subprocess.run(["pio", "project", "init", "--board", "esp32dev"], cwd=temp_dir, capture_output=True, text=True)
        if init_res.returncode != 0:
            return f"Failed to initialize firmware project:\n{init_res.stderr}"

        # Write code to src/main.cpp
        src_path = os.path.join(temp_dir, "src", "main.cpp")
        os.makedirs(os.path.dirname(src_path), exist_ok=True)
        with open(src_path, "w") as f:
            f.write(code)

        # Compile and upload
        logger.info("Compiling and flashing firmware...")
        upload_res = subprocess.run(["pio", "run", "--target", "upload"], cwd=temp_dir, capture_output=True, text=True)

        if upload_res.returncode == 0:
            return "Successfully generated and flashed the firmware to the connected ESP32!"
        else:
            logger.error(f"Firmware upload failed:\n{upload_res.stderr}")
            return f"Failed to flash the firmware. Please ensure the ESP32 is connected.\nError:\n{upload_res.stderr[-500:]}"

    finally:
        # Clean up
        shutil.rmtree(temp_dir, ignore_errors=True)
