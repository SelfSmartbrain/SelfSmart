"""
Text-to-Speech using Piper (high-quality, local, female voices)
"""
import asyncio
import subprocess
import tempfile
import os
import logging
from typing import AsyncGenerator, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class PiperTTS:
    def __init__(
        self,
        voice: str = "en_US-lessac-medium",  # Female voice
        piper_path: str = "piper",
        model_dir: str = "models/piper",
        sample_rate: int = 22050,
    ):
        self.voice = voice
        self.piper_path = Path(piper_path)
        self.model_dir = Path(model_dir)
        self.sample_rate = sample_rate
        self.model_path = self.model_dir / f"{voice}.onnx"
        self.config_path = self.model_dir / f"{voice}.onnx.json"

        if not self.model_path.exists():
            self._download_voice()

    def _download_voice(self):
        """Download Piper voice model"""
        self.model_dir.mkdir(parents=True, exist_ok=True)

        import urllib.request

        base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
        
        # Parse voice: en_US-lessac-medium -> lang=en, country=en_US, name=lessac, quality=medium
        parts = self.voice.split("-")
        if len(parts) >= 3:
            lang = parts[0]
            country = parts[1]
            name = parts[2]
            quality = parts[3] if len(parts) > 3 else "medium"
        else:
            # fallback
            lang = "en"
            country = "en_US"
            name = "lessac"
            quality = "medium"
        
        # Path format: en/en_US/lessac/medium/en_US-lessac-medium.onnx
        model_url = f"{base_url}/{lang}/{country}/{name}/{quality}/{self.voice}.onnx"
        config_url = f"{base_url}/{lang}/{country}/{name}/{quality}/{self.voice}.onnx.json"

        logger.info(f"Downloading voice {self.voice}...")
        logger.info(f"Model URL: {model_url}")
        urllib.request.urlretrieve(model_url, self.model_path)
        urllib.request.urlretrieve(config_url, self.config_path)
        logger.info("Voice downloaded")

    async def synthesize(self, text: str) -> bytes:
        """Synthesize text to audio bytes"""
        if not text.strip():
            return b""

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_file = f.name

        try:
            cmd = [
                str(self.piper_path / "piper"),
                "--model", str(self.model_path),
                "--config", str(self.config_path),
                "--output_file", output_file,
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate(input=text.encode())

            if proc.returncode != 0:
                logger.error(f"Piper error: {stderr.decode()}")
                return b""

            # Read generated WAV
            with open(output_file, "rb") as f:
                audio_data = f.read()

            return audio_data

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return b""
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    async def synthesize_stream(
        self, text_chunks: AsyncGenerator[str, None]
    ) -> AsyncGenerator[bytes, None]:
        """Stream synthesis for real-time playback"""
        buffer = ""

        async for chunk in text_chunks:
            buffer += chunk

            # Synthesize on sentence boundaries
            if any(buffer.endswith(p) for p in [".", "!", "?", "\n"]):
                audio = await self.synthesize(buffer)
                if audio:
                    yield audio
                buffer = ""

        # Synthesize remaining
        if buffer.strip():
            audio = await self.synthesize(buffer)
            if audio:
                yield audio


# Alternative: Coqui TTS (if Piper not available)
class CoquiTTS:
    def __init__(self, model_name: str = "tts_models/en/ljspeech/vits"):
        self.model_name = model_name
        self._tts = None
        self._init_model()

    def _init_model(self):
        try:
            from TTS.api import TTS
            self._tts = TTS(self.model_name, gpu=False)
            logger.info(f"Coqui TTS loaded: {self.model_name}")
        except Exception as e:
            logger.error(f"Coqui TTS init failed: {e}")

    async def synthesize(self, text: str) -> bytes:
        if not self._tts or not text.strip():
            return b""

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_file = f.name

        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self._tts.tts_to_file, text, output_file
            )

            with open(output_file, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)