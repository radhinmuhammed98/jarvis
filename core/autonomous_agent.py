import os
import json
import logging
import subprocess
import sys
import tempfile
from core.ai_provider import call_ai

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Jarvis, an autonomous engineering agent capable of writing, executing, and fixing your own Python scripts to fulfill any open-ended user request.
You run on the user's local machine. You have permission to install packages using pip, interact with the system, scrape web pages, control hardware, etc.

You will be given a task. You must output ONLY a JSON object with your next action.
Do not output markdown or explanatory text outside the JSON block.

Allowed actions:
1. `{"action": "RUN_PYTHON", "code": "import requests\nprint(requests.get('https://example.com').text)"}`
   - This writes your code to a temporary file and runs it. The output will be fed back to you in the next iteration.
   - Use `subprocess.run(['pip', 'install', 'package_name'])` inside your script if you need to install a module.
   - Always print out the final result or relevant info so it goes to stdout.
2. `{"action": "DONE", "result": "The final summary of what you achieved for the user."}`
   - Use this when the task is complete. The `result` string will be spoken/shown to the user.
3. `{"action": "FAIL", "reason": "Explanation of why the task is impossible."}`
   - Use this if you are stuck after multiple attempts.

If a previous script execution returns an error, write a new script to fix the error.

Example Output (RUN_PYTHON):
```json
{"action": "RUN_PYTHON", "code": "import subprocess\nsubprocess.run(['pip', 'install', 'requests'])\nimport requests\nprint('Installed and imported requests!')"}
```

Example Output (DONE):
```json
{"action": "DONE", "result": "I successfully flashed the ESP32 and ran the test script."}
```
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

def execute_autonomous_task(task_description: str, max_iterations: int = 5) -> str:
    """Executes a loop allowing the AI to write and run code until DONE or FAIL."""
    logger.info(f"Starting autonomous task: {task_description}")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Task: {task_description}"}
    ]

    for i in range(max_iterations):
        logger.info(f"Autonomous loop iteration {i+1}/{max_iterations}")

        try:
            response = call_ai(messages, temperature=0.2)
        except Exception as e:
            logger.error(f"AI call failed in autonomous loop: {e}")
            return f"I encountered a communication error with my brain: {e}"

        messages.append({"role": "assistant", "content": response})

        action_data = extract_json(response)
        if not action_data:
            err_msg = "Invalid JSON returned. You must return only a valid JSON object."
            logger.warning(err_msg)
            messages.append({"role": "user", "content": err_msg})
            continue

        action = action_data.get("action")

        if action == "DONE":
            return action_data.get("result", "Task completed autonomously.")

        elif action == "FAIL":
            return f"I couldn't complete the task: {action_data.get('reason', 'Unknown reason')}"

        elif action == "RUN_PYTHON":
            code = action_data.get("code", "")
            logger.info("Executing generated python script...")

            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file_name = f.name

            try:
                # Run the code
                result = subprocess.run([sys.executable, temp_file_name], capture_output=True, text=True, timeout=60)
                output = result.stdout
                error = result.stderr

                feedback = ""
                if output:
                    feedback += f"STDOUT:\n{output}\n"
                if error:
                    feedback += f"STDERR:\n{error}\n"

                if not feedback:
                    feedback = "Script executed successfully with no output."

                logger.debug(f"Script feedback: {feedback}")
                messages.append({"role": "user", "content": f"Execution result:\n{feedback}"})

            except subprocess.TimeoutExpired:
                messages.append({"role": "user", "content": "Execution timed out after 60 seconds."})
            except Exception as e:
                messages.append({"role": "user", "content": f"Execution failed to run: {e}"})
            finally:
                if os.path.exists(temp_file_name):
                    os.remove(temp_file_name)

        else:
            messages.append({"role": "user", "content": f"Unknown action '{action}'."})

    return f"I stopped trying after {max_iterations} iterations without finishing."
