import webrtcvad
import numpy as np
from typing import Optional


class VoiceActivityDetector:
    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        aggressiveness: int = 2,
    ):
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self.vad = webrtcvad.Vad(aggressiveness)
        self._buffer = np.array([], dtype=np.int16)

    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        if audio_chunk.dtype != np.int16:
            audio_int16 = (audio_chunk * 32767).astype(np.int16)
        else:
            audio_int16 = audio_chunk

        self._buffer = np.concatenate([self._buffer, audio_int16])

        if len(self._buffer) < self.frame_size:
            return False

        frame = self._buffer[:self.frame_size]
        self._buffer = self._buffer[self.frame_size:]

        try:
            return self.vad.is_speech(frame.tobytes(), self.sample_rate)
        except Exception:
            return False

    def reset(self):
        self._buffer = np.array([], dtype=np.int16)

    def process_stream(
        self, audio_chunk: np.ndarray, min_speech_frames: int = 3
    ) -> tuple[bool, Optional[np.ndarray]]:
        is_speech = self.is_speech(audio_chunk)

        return is_speech, audio_chunk if is_speech else None


class StreamingVAD:
    def __init__(
        self,
        sample_rate: int = 16000,
        aggressiveness: int = 2,
        padding_ms: int = 300,
        min_speech_ms: int = 250,
        max_silence_ms: int = 1000,
    ):
        self.vad = VoiceActivityDetector(sample_rate, aggressiveness=aggressiveness)
        self.sample_rate = sample_rate
        self.padding_frames = int(padding_ms * sample_rate / 1000)
        self.min_speech_frames = int(min_speech_ms * sample_rate / 1000)
        self.max_silence_frames = int(max_silence_ms * sample_rate / 1000)

        self._speech_buffer = []
        self._silence_frames = 0
        self._speech_frames = 0
        self._triggered = False

    def process(self, audio_chunk: np.ndarray) -> Optional[np.ndarray]:
        if audio_chunk.dtype != np.int16:
            audio_int16 = (audio_chunk * 32767).astype(np.int16)
        else:
            audio_int16 = audio_chunk

        is_speech = self.vad.is_speech(audio_int16)

        if is_speech:
            self._silence_frames = 0
            self._speech_frames += len(audio_int16)
            self._speech_buffer.append(audio_int16)

            if not self._triggered and self._speech_frames >= self.min_speech_frames:
                self._triggered = True
        else:
            if self._triggered:
                self._silence_frames += len(audio_int16)
                self._speech_buffer.append(audio_int16)

                if self._silence_frames >= self.max_silence_frames:
                    result = np.concatenate(self._speech_buffer)
                    self._reset()
                    return result
            else:
                self._speech_buffer = []

        return None

    def _reset(self):
        self._speech_buffer = []
        self._silence_frames = 0
        self._speech_frames = 0
        self._triggered = False
        self.vad.reset()

    def force_flush(self) -> Optional[np.ndarray]:
        if self._speech_buffer and self._speech_frames >= self.min_speech_frames:
            result = np.concatenate(self._speech_buffer)
            self._reset()
            return result
        self._reset()
        return None