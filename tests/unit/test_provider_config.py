"""Provider configuration tests."""

from unittest.mock import patch

from pydantic import SecretStr

from src.config.settings import Settings
from src.coding.patch_generator import PatchGenerator


def test_settings_normalizes_openrouter_anthropic_base_url():
    """OpenRouter's Anthropic-compatible endpoint must not include /v1."""
    settings = Settings(
        _env_file=None,
        anthropic_api_key=SecretStr("sk-or-v1-test"),
        openai_api_key=SecretStr("sk-test"),
        anthropic_base_url="https://openrouter.ai/api/v1/",
        anthropic_model="anthropic/claude-sonnet-4.6",
    )

    assert settings.anthropic_base_url == "https://openrouter.ai/api"


def test_patch_generator_uses_configured_provider_settings():
    """PatchGenerator should pass provider settings directly to ChatAnthropic."""
    settings = Settings(
        _env_file=None,
        anthropic_api_key=SecretStr("sk-or-v1-test"),
        openai_api_key=SecretStr("sk-test"),
        anthropic_base_url="https://openrouter.ai/api/v1",
        anthropic_model="anthropic/claude-sonnet-4.6",
        llm_max_tokens=2048,
    )
    with (
        patch("src.coding.patch_generator.ChatAnthropic") as chat_cls,
        patch("src.config.settings.get_settings", return_value=settings),
    ):
        PatchGenerator("/tmp/repo")

        chat_cls.assert_called_once_with(
            model="anthropic/claude-sonnet-4.6",
            api_key="sk-or-v1-test",
            temperature=0.1,
            max_tokens=2048,
            base_url="https://openrouter.ai/api",
        )
