import os
import json
import time
import shutil
import logging
import subprocess
from pathlib import Path
from core.ai_provider import call_ai

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

ALLOWED_PATHS = [
    "core",
    "modules",
    "utils",
    "main.py",
    "requirements.txt",
    "README.md",
    "esp32",
]

BLOCKED_PATHS = [
    ".env",
    "__pycache__",
    ".git",
    "backups"
]

def is_path_allowed(filepath: str) -> bool:
    """Check if the given filepath is within allowed directories and not blocked."""
    abs_path = os.path.abspath(os.path.join(PROJECT_ROOT, filepath))
    
    # Must be inside project root
    if not abs_path.startswith(PROJECT_ROOT):
        return False
        
    rel_path = os.path.relpath(abs_path, PROJECT_ROOT)
    
    # Check blocked
    for b in BLOCKED_PATHS:
        if rel_path.startswith(b) or f"/{b}/" in f"/{rel_path}":
            return False
            
    # Check allowed
    for a in ALLOWED_PATHS:
        if rel_path == a or rel_path.startswith(a + "/"):
            return True
            
    return False

def read_project_tree() -> str:
    """Generate a file tree of the allowed directories."""
    tree = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Filter out blocked directories
        dirs[:] = [d for d in dirs if not any(b in d for b in BLOCKED_PATHS)]
        
        for file in files:
            if any(b in file for b in BLOCKED_PATHS) or file.endswith(".db"):
                continue
            
            rel_path = os.path.relpath(os.path.join(root, file), PROJECT_ROOT)
            if is_path_allowed(rel_path):
                tree.append(rel_path)
    return "\n".join(sorted(tree))

def read_file(filepath: str) -> str:
    if not is_path_allowed(filepath):
        raise ValueError(f"Access to {filepath} is blocked.")
    full_path = os.path.join(PROJECT_ROOT, filepath)
    if not os.path.exists(full_path):
        return ""
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()

def backup_file(filepath: str) -> str | None:
    """Backup a file before editing it. Returns backup path or None if file didn't exist."""
    full_path = os.path.join(PROJECT_ROOT, filepath)
    if not os.path.exists(full_path):
        return None
        
    backup_dir = os.path.join(PROJECT_ROOT, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    
    # Flatten path for backup name: core/executor.py -> core_executor.py
    safe_name = filepath.replace("/", "_").replace("\\", "_")
    timestamp = int(time.time())
    backup_path = os.path.join(backup_dir, f"{safe_name}.{timestamp}.bak")
    
    shutil.copy2(full_path, backup_path)
    logger.info(f"Backed up {filepath} to {backup_path}")
    return backup_path

def write_file(filepath: str, content: str):
    if not is_path_allowed(filepath):
        raise ValueError(f"Access to {filepath} is blocked.")
    
    full_path = os.path.join(PROJECT_ROOT, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

def run_checks() -> str | None:
    """Run python compilation checks on core files. Returns error string if failed, None if success."""
    cmd = ["python", "-m", "py_compile", "main.py"]
    
    # Find all .py files in core, modules, utils
    for d in ["core", "modules", "utils"]:
        d_path = os.path.join(PROJECT_ROOT, d)
        if os.path.exists(d_path):
            for root, _, files in os.walk(d_path):
                for f in files:
                    if f.endswith(".py"):
                        cmd.append(os.path.join(root, f))
                        
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, check=True)
        return None # Success
    except subprocess.CalledProcessError as e:
        return e.stderr or e.stdout

def _parse_ai_response(response: str) -> list[dict]:
    """Extract JSON blocks containing file changes from the AI response."""
    # Look for ```json ... ``` blocks
    import re
    matches = re.findall(r"```json\s*(.*?)\s*```", response, re.DOTALL)
    
    changes = []
    for match in matches:
        try:
            data = json.loads(match)
            if isinstance(data, list):
                changes.extend(data)
            elif isinstance(data, dict):
                changes.append(data)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON block from AI response.")
            continue
    return changes

def run_developer_task(task: str) -> str:
    """Execute a developer task to self-modify the codebase."""
    logger.info(f"Running developer task: {task}")
    
    tree = read_project_tree()
    
    system_prompt = f"""You are the Developer Agent for Jarvis, an autonomous smart assistant.
The user has requested a codebase modification.

YOUR GOAL:
Generate full file replacements to implement the requested feature or fix.

PROJECT CONTEXT:
The project root is `{PROJECT_ROOT}`.
Here are the allowed files you can modify:
{tree}

RULES:
1. You must ONLY output JSON blocks containing the file changes.
2. The JSON MUST be an array of objects, with each object having exactly two keys: "file" (the relative path) and "content" (the FULL new file content as a string).
3. Do NOT use complex diff patching, output the FULL ENTIRE file content.
4. You are strictly forbidden from modifying `.env` or printing any API keys.
5. Provide NO additional explanation or text outside the JSON block.
"""

    # Provide context of files mentioned in the task to help the AI
    context_content = ""
    for f in tree.split("\n"):
        if f and (f in task or os.path.basename(f) in task):
            try:
                content = read_file(f)
                context_content += f"\n--- {f} ---\n{content}\n"
            except Exception:
                pass


    system_prompt += f"\nCURRENT FILE CONTENTS FOR CONTEXT:\n{context_content}\n"
    
    user_prompt = f"User Request: {task}\n\nPlease generate the JSON array of file changes. Wrap the JSON in ```json\n...\n``` tags."
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        response = call_ai(messages, temperature=0.2)
        changes = _parse_ai_response(response)
        
        if not changes:
            return "I couldn't generate the code changes required for that task. The AI didn't return valid JSON."
            
        backed_up_files = {}
        changed_files = []
        
        for change in changes:
            filepath = change.get("file")
            content = change.get("content")
            
            if not filepath or not content:
                continue
                
            if not is_path_allowed(filepath):
                logger.warning(f"AI attempted to modify blocked path: {filepath}")
                continue
                
            # Backup
            bak = backup_file(filepath)
            backed_up_files[filepath] = bak
            
            # Write
            write_file(filepath, content)
            changed_files.append(filepath)
            
        if not changed_files:
            return "I generated a response, but no valid file changes were applied."
            
        # Validate
        error = run_checks()
        if error:
            logger.error(f"Validation failed after edits:\n{error}")
            # Rollback
            for filepath, bak_path in backed_up_files.items():
                if bak_path and os.path.exists(bak_path):
                    shutil.copy2(bak_path, os.path.join(PROJECT_ROOT, filepath))
                else:
                    # File was newly created, delete it
                    full_path = os.path.join(PROJECT_ROOT, filepath)
                    if os.path.exists(full_path):
                        os.remove(full_path)
            return f"I tried to update the code, but validation failed, so I restored the backup. Error: {error}"
            
        return f"I updated the code. Changed files: {', '.join(changed_files)}. Tests passed."
        
    except Exception as e:
        logger.error(f"Developer task failed: {e}")
        return f"An error occurred during the developer task: {str(e)}"
