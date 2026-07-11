import asyncio
import json
import os
from pathlib import Path
from typing import Optional, Dict, List
import numpy as np
import piper
import piper.config
import logging

logger = logging.getLogger(__name__)


class PiperSynthesizer:
    VOICE_CONFIG = {
        "casual": "en_US-amy-low.onnx",
        "professional": "en_US-lessac-medium.onnx",
        "clear": "en_US-libritts-medium.onnx",
    }

    DEFAULT_VOICE = "clear"

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        voices_dir: Optional[Path] = None,
        length_scale: float = 1.0,
        noise_scale: float = 0.667,
        noise_w_scale: float = 0.8,
    ):
        self.voice_name = voice
        self.voices_dir = voices_dir or Path(__file__).parent.parent / "voices"
        self.length_scale = length_scale
        self.noise_scale = noise_scale
        self.noise_w_scale = noise_w_scale
        self._voice: Optional[piper.PiperVoice] = None
        self._sample_rate = 22050

    def _load_voice(self):
        if self._voice is None:
            voice_file = self.VOICE_CONFIG.get(self.voice_name, self.VOICE_CONFIG[self.DEFAULT_VOICE])
            voice_path = self.voices_dir / voice_file
            config_path = voice_path.with_suffix(".onnx.json")

            if not voice_path.exists():
                raise FileNotFoundError(f"Voice model not found: {voice_path}")

            logger.info(f"Loading Piper voice: {voice_file}")
            self._voice = piper.PiperVoice.load(str(voice_path), config_path=str(config_path) if config_path.exists() else None)
            self._sample_rate = self._voice.config.sample_rate
            logger.info(f"Voice loaded, sample rate: {self._sample_rate}")

    def set_voice(self, voice: str):
        if voice in self.VOICE_CONFIG:
            self.voice_name = voice
            self._voice = None
            self._load_voice()
        else:
            raise ValueError(f"Unknown voice: {voice}. Available: {list(self.VOICE_CONFIG.keys())}")

    def synthesize(self, text: str) -> np.ndarray:
        self._load_voice()
        
        synthesis_config = piper.config.SynthesisConfig(
            length_scale=self.length_scale,
            noise_scale=self.noise_scale,
            noise_w_scale=self.noise_w_scale,
        )
        
        audio_chunks = []
        for audio_chunk in self._voice.synthesize(text, syn_config=synthesis_config):
            audio_chunks.append(audio_chunk.audio_float_array)
        
        audio = np.concatenate(audio_chunks).astype(np.float32)
        return audio

    async def synthesize_async(self, text: str) -> np.ndarray:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.synthesize, text)

    def synthesize_stream(self, text: str):
        self._load_voice()
        
        synthesis_config = piper.config.SynthesisConfig(
            length_scale=self.length_scale,
            noise_scale=self.noise_scale,
            noise_w_scale=self.noise_w_scale,
        )
        
        for audio_chunk in self._voice.synthesize(text, syn_config=synthesis_config):
            yield audio_chunk.audio_float_array

    @property
    def sample_rate(self) -> int:
        if self._voice is None:
            self._load_voice()
        return self._sample_rate

    @classmethod
    def list_voices(cls, voices_dir: Optional[Path] = None) -> Dict[str, str]:
        voices_dir = voices_dir or Path(__file__).parent.parent / "voices"
        available = {}
        for profile, filename in cls.VOICE_CONFIG.items():
            path = voices_dir / filename
            if path.exists():
                available[profile] = filename
        return available


class VoiceManager:
    def __init__(self, voices_dir: Optional[Path] = None):
        self.voices_dir = voices_dir or Path(__file__).parent.parent / "voices"
        self._synthesizers: Dict[str, PiperSynthesizer] = {}

    def get_synthesizer(self, voice_profile: str = "clear") -> PiperSynthesizer:
        if voice_profile not in self._synthesizers:
            self._synthesizers[voice_profile] = PiperSynthesizer(
                voice=voice_profile, voices_dir=self.voices_dir
            )
        return self._synthesizers[voice_profile]

    def list_available_voices(self) -> Dict[str, str]:
        return PiperSynthesizer.list_voices(self.voices_dir)

    def download_voice(self, voice_profile: str) -> bool:
        """Placeholder for voice downloading"""
        logger.warning(f"Voice download not implemented for {voice_profile}")
        return False