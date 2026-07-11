#!/usr/bin/env python3
"""
ModelX Voice Assistant - Main Entry Point

Run: python -m src.voice_assistant.main
Or: python src/voice_assistant/main.py
"""

import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.voice_assistant.server import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point"""
    import uvicorn

    logger.info("Starting ModelX Voice Assistant...")

    # Check for required models
    check_models()

    # Run server
    uvicorn.run(
        "src.voice_assistant.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )


def check_models():
    """Check and download required models"""
    models_dir = os.path.join(os.path.dirname(__file__), "models")
    os.makedirs(models_dir, exist_ok=True)

    # Whisper model
    whisper_model = os.path.join(models_dir, "ggml-base.en.bin")
    if not os.path.exists(whisper_model):
        logger.info("Whisper model not found. Please download:")
        logger.info("  wget -P models https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin")
        logger.info("  Or run: python -m src.voice_assistant.download_models")

    # Piper voice
    piper_model = os.path.join(models_dir, "piper", "en_US-lessac-medium.onnx")
    if not os.path.exists(piper_model):
        logger.info("Piper voice not found. Please download:")
        logger.info("  mkdir -p models/piper")
        logger.info("  wget -P models/piper https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx")
        logger.info("  wget -P models/piper https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json")


if __name__ == "__main__":
    main()