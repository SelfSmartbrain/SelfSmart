"""Tests for audio components (mocked, no hardware required)."""
import pytest
import numpy as np
from unittest.mock import patch, MagicMock, AsyncMock

from modelx_voice.audio.vad import VoiceActivityDetector, StreamingVAD


class TestVoiceActivityDetector:
    def setup_method(self):
        self.vad = VoiceActivityDetector(
            sample_rate=16000,
            frame_duration_ms=30,
            aggressiveness=2,
        )

    def test_init(self):
        assert self.vad.sample_rate == 16000
        assert self.vad.frame_size == 480  # 16000 * 30 / 1000

    def test_is_speech_silence(self):
        # All zeros = silence
        silence = np.zeros(480, dtype=np.float32)
        assert self.vad.is_speech(silence) is False

    def test_is_speech_noise(self):
        # Random noise (should not be detected as speech by WebRTC VAD)
        noise = np.random.normal(0, 0.01, 480).astype(np.float32)
        result = self.vad.is_speech(noise)
        assert isinstance(result, bool)

    def test_is_speech_int16(self):
        # Test with int16 input
        silence = np.zeros(480, dtype=np.int16)
        assert self.vad.is_speech(silence) is False

    def test_reset(self):
        self.vad._buffer = np.ones(100, dtype=np.int16)
        self.vad.reset()
        assert len(self.vad._buffer) == 0

    def test_process_stream(self):
        chunk = np.random.normal(0, 0.1, 1000).astype(np.float32)
        is_speech, audio = self.vad.process_stream(chunk)
        assert isinstance(is_speech, bool)
        if is_speech:
            assert audio is not None
        else:
            assert audio is None


class TestStreamingVAD:
    def setup_method(self):
        self.vad = StreamingVAD(
            sample_rate=16000,
            aggressiveness=2,
            padding_ms=300,
            min_speech_ms=250,
            max_silence_ms=1000,
        )

    def test_init(self):
        assert self.vad.sample_rate == 16000
        assert self.vad.padding_frames == 4800  # 16000 * 300 / 1000
        assert self.vad.min_speech_frames == 4000
        assert self.vad.max_silence_frames == 16000

    def test_process_silence(self):
        # Feed silence chunks
        silence = np.zeros(512, dtype=np.float32)
        for _ in range(5):
            result = self.vad.process(silence)
            assert result is None

    def test_process_speech_like(self):
        # Create chunk with enough energy to potentially trigger VAD
        # WebRTC VAD needs actual speech-like patterns
        speech_like = np.random.normal(0, 0.5, 512).astype(np.float32)
        result = self.vad.process(speech_like)
        # Result depends on VAD internals, just verify it runs
        assert result is None or isinstance(result, np.ndarray)

    def test_force_flush(self):
        # Add some data to buffer
        self.vad._speech_buffer = [np.ones(100, dtype=np.int16)]
        self.vad._speech_frames = 100
        self.vad._triggered = True

        result = self.vad.force_flush()
        assert isinstance(result, np.ndarray)
        assert len(result) == 100

        # Buffer should be reset
        assert self.vad._speech_buffer == []
        assert self.vad._speech_frames == 0

    def test_force_flush_empty(self):
        result = self.vad.force_flush()
        assert result is None

    def test_reset(self):
        self.vad._speech_buffer = [np.ones(100, dtype=np.int16)]
        self.vad._silence_frames = 100
        self.vad._speech_frames = 100
        self.vad._triggered = True

        self.vad._reset()

        assert self.vad._speech_buffer == []
        assert self.vad._silence_frames == 0
        assert self.vad._speech_frames == 0
        assert self.vad._triggered is False