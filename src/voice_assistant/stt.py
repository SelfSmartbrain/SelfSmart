"""
Speech-to-Text using Whisper.cpp (local, fast)
"""
import asyncio
import subprocess
import tempfile
import os
import logging
from typing import Optional, AsyncGenerator
from pathlib import Path

logger = logging.getLogger(__name__)


class WhisperSTT:
    def __init__(
        self,
        model_path: str = "models/ggml-base.en.bin",
        whisper_cpp_path: str = "whisper.cpp",
        language: str = "en",
        threads: int = 4,
    ):
        self.model_path = Path(model_path)
        self.whisper_cpp_path = Path(whisper_cpp_path)
        self.language = language
        self.threads = threads
        self._process = None

        # Download model if needed
        if not self.model_path.exists():
            self._download_model()

    def _download_model(self):
        """Download Whisper model"""
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        import urllib.request

        url = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin"
        logger.info(f"Downloading Whisper model from {url}")
        urllib.request.urlretrieve(url, self.model_path)
        logger.info("Model downloaded")

    async def transcribe_file(self, audio_file: str) -> str:
        """Transcribe audio file to text"""
        cmd = [
            str(self.whisper_cpp_path / "main"),
            "-m", str(self.model_path),
            "-f", audio_file,
            "-l", self.language,
            "-t", str(self.threads),
            "-nt",  # no timestamps
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"Whisper error: {stderr.decode()}")
                return ""

            return stdout.decode().strip()
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return ""

    async def transcribe_audio(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """Transcribe raw audio bytes"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            # Write WAV header
            import wave
            with wave.open(f.name, 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)  # 16-bit
                wav.setframerate(sample_rate)
                wav.writeframes(audio_data)

            try:
                result = await self.transcribe_file(f.name)
                return result
            finally:
                os.unlink(f.name)

    async def transcribe_stream(
        self, audio_chunks: AsyncGenerator[bytes, None], sample_rate: int = 16000
    ) -> AsyncGenerator[str, None]:
        """Stream transcription (accumulate chunks)"""
        buffer = bytearray()
        chunk_count = 0

        async for chunk in audio_chunks:
            buffer.extend(chunk)
            chunk_count += 1

            # Process every ~3 seconds of audio
            if len(buffer) >= sample_rate * 2 * 3:  # 3 seconds at 16kHz 16-bit mono
                text = await self.transcribe_audio(bytes(buffer), sample_rate)
                if text:
                    yield text
                buffer.clear()
                chunk_count = 0

        # Process remaining
        if buffer:
            text = await self.transcribe_audio(bytes(buffer), sample_rate)
            if text:
                yield text


class VADWrapper:
    """Voice Activity Detection wrapper using Silero VAD"""
    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self._model = None
        self._init_vad()

    def _init_vad(self):
        try:
            import torch
            self._model, _ = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False
            )
        except Exception as e:
            logger.warning(f"VAD not available: {e}")

    def is_speech(self, audio_chunk: bytes, sample_rate: int = 16000) -> bool:
        if not self._model:
            return True  # No VAD, treat all as speech

        import torch
        import numpy as np

        # Convert bytes to tensor
        audio_np = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
        audio_tensor = torch.from_numpy(audio_np)

        try:
            speech_prob = self._model(audio_tensor, sample_rate).item()
            return speech_prob > self.threshold
        except Exception:
            return True