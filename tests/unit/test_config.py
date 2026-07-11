"""Tests for configuration manager."""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from modelx_voice.config import ConfigManager, ModelXConfig, APIConfig


class TestConfigManager:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_file = Path(self.temp_dir.name) / "config.json"
        self.manager = ConfigManager(config_file=self.config_file)

    def teardown_method(self):
        self.temp_dir.cleanup()

    def test_default_config(self):
        config = self.manager.load()
        assert isinstance(config, ModelXConfig)
        assert config.api.provider == "anthropic"
        assert config.voice.selected_voice == "clear"
        assert config.audio.sample_rate == 16000

    def test_save_and_load(self):
        config = self.manager.load()
        config.api.provider = "openai"
        config.api.model = "gpt-4o"
        config.voice.selected_voice = "casual"
        config.audio.input_device = 1

        with patch.object(self.manager, "save_api_key") as mock_save:
            self.manager.save()
            mock_save.assert_called_once()

        # Reload and verify
        new_manager = ConfigManager(config_file=self.config_file)
        loaded = new_manager.load()
        assert loaded.api.provider == "openai"
        assert loaded.api.model == "gpt-4o"
        assert loaded.voice.selected_voice == "casual"
        assert loaded.audio.input_device == 1

    def test_api_key_in_keyring(self):
        with patch("keyring.set_password") as mock_set, \
             patch("keyring.get_password", return_value="test-key") as mock_get:

            self.manager.save_api_key("anthropic", "test-key")
            mock_set.assert_called_once_with("modelx-voice", "anthropic", "test-key")

            key = self.manager.get_api_key("anthropic")
            assert key == "test-key"
            mock_get.assert_called_once_with("modelx-voice", "anthropic")

    def test_config_with_keyring_placeholder(self):
        # Simulate saved config with keyring placeholder
        config_data = {
            "api": {
                "provider": "anthropic",
                "api_key": "***KEYRING***",
                "model": "claude-sonnet-4",
                "base_url": None
            },
            "voice": {"selected_voice": "clear", "speed": 1.0, "pitch": 1.0},
            "audio": {"input_device": None, "output_device": None, "sample_rate": 16000},
            "behavior": {"wake_word": "hey modelx", "auto_listen": True, "response_delay": 0.5, "vad_aggressiveness": 2}
        }
        self.config_file.write_text(json.dumps(config_data))

        with patch("keyring.get_password", return_value="actual-key"):
            config = self.manager.load()
            assert config.api.api_key == "actual-key"

    def test_update_api(self):
        self.manager.update_api(provider="openai", api_key="new-key", model="gpt-4o")
        config = self.manager.load()
        assert config.api.provider == "openai"
        assert config.api.api_key == "new-key"
        assert config.api.model == "gpt-4o"

    def test_update_voice(self):
        self.manager.update_voice(selected_voice="professional", speed=1.2)
        config = self.manager.load()
        assert config.voice.selected_voice == "professional"
        assert config.voice.speed == 1.2

    def test_update_audio(self):
        self.manager.update_audio(input_device=2, output_device=3)
        config = self.manager.load()
        assert config.audio.input_device == 2
        assert config.audio.output_device == 3

    def test_update_behavior(self):
        self.manager.update_behavior(wake_word="computer", auto_listen=False, vad_aggressiveness=3)
        config = self.manager.load()
        assert config.behavior.wake_word == "computer"
        assert config.behavior.auto_listen is False
        assert config.behavior.vad_aggressiveness == 3

    def test_is_configured(self):
        assert self.manager.is_configured() is False

        with patch("keyring.set_password"):
            self.manager.update_api(api_key="test-key")
        assert self.manager.is_configured() is True

    def test_reset(self):
        with patch("keyring.set_password"):
            self.manager.update_api(api_key="test-key")
        assert self.config_file.exists()

        self.manager.reset()
        assert not self.config_file.exists()
        assert self.manager._config is None


class TestModelXConfig:
    def test_api_config_defaults(self):
        api = APIConfig()
        assert api.provider == "anthropic"
        assert api.api_key == ""
        assert api.model == ""
        assert api.base_url == ""

    def test_full_config_serialization(self):
        config = ModelXConfig()
        # Verify all nested dataclasses exist
        assert config.api is not None
        assert config.voice is not None
        assert config.audio is not None
        assert config.behavior is not None