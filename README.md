# Jarvis Assistant

A modular Python-based AI assistant.

## Architecture

- **`core/`**: Central logic including AI intent parsing and command execution.
- **`modules/`**: Pluggable components for extendability.
  - **`voice/`**: Future support for STT (Speech-to-Text) and TTS (Text-to-Speech).
  - **`esp32/`**: Future integration for IoT / ESP32 communication.
- **`utils/`**: Helper scripts like logging.

## Getting Started

1. Install any future dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run Jarvis:
   ```bash
   python main.py
   ```
# jarvis
