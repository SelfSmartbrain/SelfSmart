import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict, field
import keyring
import logging

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".modelx-voice"
CONFIG_FILE = CONFIG_DIR / "config.json"
VOICES_DIR = CONFIG_DIR / "voices"


@dataclass
class APIConfig:
    provider: str = "anthropic"
    api_key: str = ""
    model: str = ""
    base_url: str = ""


@dataclass
class VoiceConfig:
    selected_voice: str = "clear"
    speed: float = 1.0
    pitch: float = 1.0


@dataclass
class AudioConfig:
    input_device: Optional[int] = None
    output_device: Optional[int] = None
    sample_rate: int = 16000


@dataclass
class BehaviorConfig:
    wake_word: str = "hey modelx"
    auto_listen: bool = True
    response_delay: float = 0.5
    vad_aggressiveness: int = 2


@dataclass
class ModelXConfig:
    api: APIConfig = field(default_factory=APIConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)


class ConfigManager:
    KEYRING_SERVICE = "modelx-voice"

    def __init__(self, config_file: Path = None):
        self.config_file = config_file or CONFIG_FILE
        self.config_dir = self.config_file.parent
        self._config: Optional[ModelXConfig] = None

    def load(self) -> ModelXConfig:
        if self._config is not None:
            return self._config

        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                self._config = self._deserialize(data)
            except Exception as e:
                logger.warning(f"Failed to load config: {e}")
                self._config = ModelXConfig()
        else:
            self._config = ModelXConfig()

        return self._config

    def _deserialize(self, data: Dict[str, Any]) -> ModelXConfig:
        api_data = data.get("api", {})
        if api_data.get("api_key") == "***KEYRING***":
            api_data["api_key"] = self.get_api_key(api_data.get("provider", "anthropic")) or ""

        return ModelXConfig(
            api=APIConfig(**api_data),
            voice=VoiceConfig(**data.get("voice", {})),
            audio=AudioConfig(**data.get("audio", {})),
            behavior=BehaviorConfig(**data.get("behavior", {})),
        )

    def save(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)

        config = self.load()
        data = {
            "api": asdict(config.api),
            "voice": asdict(config.voice),
            "audio": asdict(config.audio),
            "behavior": asdict(config.behavior),
        }

        provider = config.api.provider
        self.save_api_key(provider, config.api.api_key)
        if config.api.api_key:
            data["api"]["api_key"] = "***KEYRING***"
        else:
            data["api"]["api_key"] = ""

        with open(self.config_file, "w") as f:
            json.dump(data, f, indent=2)

    def get_api_key(self, provider: str) -> Optional[str]:
        try:
            return keyring.get_password(self.KEYRING_SERVICE, provider)
        except Exception as e:
            logger.warning(f"Failed to retrieve API key from keyring: {e}")
            return None

    def save_api_key(self, provider: str, api_key: str):
        if not api_key:
            self.delete_api_key(provider)
            return
        try:
            keyring.set_password(self.KEYRING_SERVICE, provider, api_key)
        except Exception as e:
            logger.error(f"Failed to save API key to keyring: {e}")
            raise

    def delete_api_key(self, provider: str):
        try:
            keyring.delete_password(self.KEYRING_SERVICE, provider)
        except Exception:
            pass

    @property
    def config(self) -> ModelXConfig:
        return self.load()

    def update_api(
        self, provider: str = None, api_key: str = None, model: str = None, base_url: str = None
    ):
        config = self.load()
        if provider is not None:
            config.api.provider = provider
        if api_key is not None:
            config.api.api_key = api_key
        if model is not None:
            config.api.model = model
        if base_url is not None:
            config.api.base_url = base_url
        self.save()

    def update_voice(self, selected_voice: str = None, speed: float = None, pitch: float = None):
        config = self.load()
        if selected_voice is not None:
            config.voice.selected_voice = selected_voice
        if speed is not None:
            config.voice.speed = speed
        if pitch is not None:
            config.voice.pitch = pitch
        self.save()

    def update_audio(
        self, input_device: int = None, output_device: int = None, sample_rate: int = None
    ):
        config = self.load()
        if input_device is not None:
            config.audio.input_device = input_device
        if output_device is not None:
            config.audio.output_device = output_device
        if sample_rate is not None:
            config.audio.sample_rate = sample_rate
        self.save()

    def update_behavior(self, **kwargs):
        config = self.load()
        for key, value in kwargs.items():
            if hasattr(config.behavior, key):
                setattr(config.behavior, key, value)
        self.save()

    def is_configured(self) -> bool:
        config = self.load()
        return bool(config.api.api_key)

    def reset(self):
        if self.config_file.exists():
            self.config_file.unlink()
        self._config = None
