#!/usr/bin/env python3
"""
Download required models for Voice Assistant
"""

import os
import sys
import urllib.request
from pathlib import Path

MODELS_DIR = Path(__file__).parent / "models"

MODELS = {
    "whisper": {
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin",
        "path": MODELS_DIR / "ggml-base.en.bin",
        "size_mb": 142
    },
    "piper_model": {
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
        "path": MODELS_DIR / "piper" / "en_US-lessac-medium.onnx",
        "size_mb": 54
    },
    "piper_config": {
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json",
        "path": MODELS_DIR / "piper" / "en_US-lessac-medium.onnx.json",
        "size_mb": 0.1
    }
}


def download_file(url: str, path: Path, size_mb: float):
    """Download file with progress"""
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        print(f"✓ Already exists: {path.name}")
        return True

    print(f"Downloading {path.name} ({size_mb:.1f} MB)...")

    try:
        def progress_hook(block_num, block_size, total_size):
            if total_size > 0:
                percent = min(100, (block_num * block_size * 100) // total_size)
                sys.stdout.write(f"\r  Progress: {percent}%")
                sys.stdout.flush()

        urllib.request.urlretrieve(url, path, reporthook=progress_hook)
        print(f"\n✓ Downloaded: {path.name}")
        return True
    except Exception as e:
        print(f"\n✗ Failed: {e}")
        return False


def main():
    print("=" * 50)
    print("ModelX Voice Assistant - Model Downloader")
    print("=" * 50)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    all_success = True
    for name, info in MODELS.items():
        success = download_file(info["url"], info["path"], info["size_mb"])
        all_success = all_success and success

    print()
    if all_success:
        print("✓ All models downloaded successfully!")
        print(f"Models saved to: {MODELS_DIR}")
    else:
        print("✗ Some downloads failed. Please retry.")
        sys.exit(1)


if __name__ == "__main__":
    main()