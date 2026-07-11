import asyncio
import numpy as np
from faster_whisper import WhisperModel
from typing import Optional, AsyncGenerator
import logging

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "auto",
        language: Optional[str] = None,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self._model: Optional[WhisperModel] = None

    def _load_model(self):
        if self._model is None:
            logger.info(f"Loading Whisper model: {self.model_size}")
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            logger.info("Whisper model loaded")

    def transcribe(self, audio_data: np.ndarray) -> str:
        self._load_model()
        
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        
        if audio_data.max() > 1.0:
            audio_data = audio_data / 32768.0

        segments, info = self._model.transcribe(
            audio_data,
            language=self.language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        text = " ".join(segment.text for segment in segments)
        return text.strip()

    async def transcribe_async(self, audio_data: np.ndarray) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.transcribe, audio_data)


class StreamingTranscriber:
    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "auto",
        language: Optional[str] = None,
        chunk_length: int = 30,
    ):
        self.transcriber = WhisperTranscriber(
            model_size, device, compute_type, language
        )
        self.chunk_length = chunk_length
        self._buffer = np.array([], dtype=np.float32)
        self.sample_rate = 16000

    def add_audio(self, audio_chunk: np.ndarray):
        if audio_chunk.dtype != np.float32:
            audio_chunk = audio_chunk.astype(np.float32)
        if audio_chunk.max() > 1.0:
            audio_chunk = audio_chunk / 32768.0
        self._buffer = np.concatenate([self._buffer, audio_chunk])

    def get_transcription(self) -> Optional[str]:
        if len(self._buffer) < self.sample_rate * 0.5:
            return None

        text = self.transcriber.transcribe(self._buffer)
        self._buffer = np.array([], dtype=np.float32)
        return text if text else None

    async def get_transcription_async(self) -> Optional[str]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_transcription)

    def reset(self):
        self._buffer = np.array([], dtype=np.float32)