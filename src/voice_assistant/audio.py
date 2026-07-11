"""
Audio I/O Manager - Handles microphone input and speaker output
"""
import asyncio
import pyaudio
import numpy as np
import logging
from typing import AsyncGenerator, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    format: int = pyaudio.paInt16
    input_device_index: Optional[int] = None
    output_device_index: Optional[int] = None


class AudioManager:
    def __init__(self, config: AudioConfig = None):
        self.config = config or AudioConfig()
        self.pyaudio = pyaudio.PyAudio()
        self._input_stream = None
        self._output_stream = None
        self._recording = False

    def list_devices(self):
        """List available audio devices"""
        for i in range(self.pyaudio.get_device_count()):
            info = self.pyaudio.get_device_info_by_index(i)
            print(f"Device {i}: {info['name']} (in:{info['maxInputChannels']} out:{info['maxOutputChannels']})")

    async def start_recording(self) -> AsyncGenerator[bytes, None]:
        """Start recording audio from microphone"""
        self._input_stream = self.pyaudio.open(
            format=self.config.format,
            channels=self.config.channels,
            rate=self.config.sample_rate,
            input=True,
            input_device_index=self.config.input_device_index,
            frames_per_buffer=self.config.chunk_size,
        )
        self._recording = True
        logger.info("Recording started")

        try:
            while self._recording:
                data = await asyncio.get_event_loop().run_in_executor(
                    None, self._input_stream.read, self.config.chunk_size, False
                )
                yield data
        finally:
            await self.stop_recording()

    async def stop_recording(self):
        """Stop recording"""
        self._recording = False
        if self._input_stream:
            self._input_stream.stop_stream()
            self._input_stream.close()
            self._input_stream = None
        logger.info("Recording stopped")

    async def play_audio(self, audio_data: bytes):
        """Play audio through speakers"""
        if not self._output_stream:
            self._output_stream = self.pyaudio.open(
                format=self.config.format,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                output=True,
                output_device_index=self.config.output_device_index,
            )

        await asyncio.get_event_loop().run_in_executor(
            None, self._output_stream.write, audio_data
        )

    async def play_audio_stream(self, audio_chunks: AsyncGenerator[bytes, None]):
        """Play streaming audio"""
        if not self._output_stream:
            self._output_stream = self.pyaudio.open(
                format=self.config.format,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                output=True,
                output_device_index=self.config.output_device_index,
            )

        async for chunk in audio_chunks:
            await asyncio.get_event_loop().run_in_executor(
                None, self._output_stream.write, chunk
            )

    def cleanup(self):
        """Cleanup audio resources"""
        if self._input_stream:
            self._input_stream.close()
        if self._output_stream:
            self._output_stream.close()
        self.pyaudio.terminate()