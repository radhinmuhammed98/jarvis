import os
import json
import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent.parent / "modules" / "skills"

def _ensure_skills_dir():
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    init_file = SKILLS_DIR / "__init__.py"
    if not init_file.exists():
        init_file.touch()

def save_skill(skill_name: str, code: str, description: str) -> bool:
    """Saves a Python script as a permanent skill."""
    _ensure_skills_dir()

    # Sanitize name
    safe_name = "".join(c if c.isalnum() else "_" for c in skill_name).lower()

    # Check for empty or just whitespace
    if not safe_name.strip('_'):
        logger.error(f"Invalid skill name: {skill_name}")
        return False

    script_path = SKILLS_DIR / f"{safe_name}.py"
    meta_path = SKILLS_DIR / f"{safe_name}.json"

    try:
        with open(script_path, "w") as f:
            f.write(code)

        with open(meta_path, "w") as f:
            json.dump({"name": skill_name, "description": description}, f, indent=4)

        logger.info(f"Saved new skill: {skill_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to save skill {skill_name}: {e}")
        return False

def list_skills() -> list[dict]:
    """Returns a list of all learned skills."""
    _ensure_skills_dir()
    skills = []

    for f in SKILLS_DIR.iterdir():
        if f.name.endswith(".json"):
            try:
                with open(f, "r") as file:
                    skills.append(json.load(file))
            except Exception as e:
                logger.warning(f"Failed to read skill metadata {f}: {e}")

    return skills

def execute_skill(skill_name: str, args: str = "") -> str:
    """Executes a saved skill script."""
    _ensure_skills_dir()
    safe_name = "".join(c if c.isalnum() else "_" for c in skill_name).lower()
    script_path = SKILLS_DIR / f"{safe_name}.py"

    if not script_path.exists():
        return f"I don't have a skill named {skill_name}."

    logger.info(f"Executing skill: {skill_name}")

    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args.split())

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        output = result.stdout
        error = result.stderr

        feedback = ""
        if output:
            feedback += f"{output}\n"
        if error:
            feedback += f"Error:\n{error}\n"

        if not feedback:
            feedback = f"Skill '{skill_name}' executed successfully with no output."

        return feedback.strip()
    except subprocess.TimeoutExpired:
        return f"Skill '{skill_name}' timed out after 120 seconds."
    except Exception as e:
        return f"Failed to execute skill '{skill_name}': {e}"
