import asyncio
import sounddevice as sd
import numpy as np
from typing import Optional, Callable
import threading
import queue


class AudioCapture:
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        device: Optional[int] = None,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.device = device
        self._stream: Optional[sd.InputStream] = None
        self._running = False
        self._audio_queue: asyncio.Queue = asyncio.Queue()
        self._callback_queue = queue.Queue()

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Audio callback status: {status}")
        if self._running:
            try:
                self._callback_queue.put_nowait(indata.copy())
            except queue.Full:
                pass

    async def start(self):
        self._running = True
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            blocksize=self.chunk_size,
            device=self.device,
            callback=self._audio_callback,
            dtype=np.float32,
        )
        self._stream.start()

    async def stop(self):
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    async def read_chunk(self) -> np.ndarray:
        loop = asyncio.get_event_loop()
        chunk = await loop.run_in_executor(None, self._callback_queue.get)
        return chunk.flatten()

    def get_devices(self):
        return sd.query_devices()

    @property
    def is_running(self) -> bool:
        return self._running


class AudioPlayback:
    def __init__(
        self,
        sample_rate: int = 22050,
        channels: int = 1,
        device: Optional[int] = None,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device
        self._stream: Optional[sd.OutputStream] = None

    async def start(self):
        self._stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            device=self.device,
            dtype=np.float32,
        )
        self._stream.start()

    async def stop(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    async def play(self, audio_data: np.ndarray):
        if self._stream is None:
            await self.start()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._stream.write, audio_data.astype(np.float32))

    def get_devices(self):
        return sd.query_devices()