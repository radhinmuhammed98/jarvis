import asyncio
import logging
import os
import shutil
import tempfile

from core.config import JARVIS_VOICE_ENABLED, JARVIS_VOICE_NAME, JARVIS_VOICE_RATE

logger = logging.getLogger(__name__)

def is_voice_enabled() -> bool:
    return JARVIS_VOICE_ENABLED

def _get_player() -> str | None:
    """Detect an available audio player on the system."""
    for player in ["ffplay", "mpg123", "mpv"]:
        if shutil.which(player):
            return player
    return None

async def _generate_and_play(text: str):
    """Generate speech with edge-tts and play it."""
    try:
        import edge_tts
    except ImportError:
        logger.error("edge-tts is not installed. Run: pip install edge-tts")
        return

    voice = JARVIS_VOICE_NAME
    rate  = JARVIS_VOICE_RATE

    player = _get_player()
    if not player:
        msg = "No supported audio player found. Install mpg123, mpv, or ffplay."
        logger.warning(msg)
        print(f"Jarvis: {msg}")
        return
    
    logger.debug(f"Found audio player: {player}")

    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp_path = tmp.name
    tmp.close()
    logger.debug(f"Temporary audio path: {tmp_path}")

    try:
        logger.debug(f"Generating TTS for: {text[:30]}...")
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(tmp_path)

        import subprocess
        
        cmd = []
        if player == "ffplay":
            cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", tmp_path]
        elif player == "mpg123":
            cmd = ["mpg123", "-q", tmp_path]
        elif player == "mpv":
            cmd = ["mpv", "--no-video", "--really-quiet", tmp_path]

        logger.debug(f"Executing playback command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

    except Exception as e:
        logger.error(f"TTS playback failed: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

def speak(text: str) -> None:
    """Speak the given text using edge-tts. Non-blocking wrapper."""
    if not text or not text.strip():
        return
    
    enabled = is_voice_enabled()
    if not enabled:
        return

    print(f"(Speaking...)")
    try:
        asyncio.run(_generate_and_play(text))
    except Exception as e:
        logger.error(f"TTS speak() failed: {e}")
