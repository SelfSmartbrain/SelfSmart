"""Tests for brain components (mocked LLM providers)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from modelx_voice.brain.llm_client import (
    Message,
    LLMResponse,
    LLMProvider,
    AnthropicProvider,
    OpenAIProvider,
    OllamaProvider,
    get_provider,
    get_default_model,
    list_providers,
)


class TestLLMDataClasses:
    def test_message(self):
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_llm_response(self):
        resp = LLMResponse(
            content="Test response",
            usage={"input_tokens": 10, "output_tokens": 20},
            model="test-model",
        )
        assert resp.content == "Test response"
        assert resp.usage["input_tokens"] == 10
        assert resp.model == "test-model"


class TestProviderFactory:
    def test_list_providers(self):
        providers = list_providers()
        assert "anthropic" in providers
        assert "openai" in providers
        assert "openrouter" in providers
        assert "ollama" in providers

    def test_get_default_model(self):
        assert get_default_model("anthropic") == "claude-sonnet-4-20250514"
        assert get_default_model("openai") == "gpt-4o"
        assert get_default_model("openrouter") == "anthropic/claude-sonnet-4"
        assert get_default_model("ollama") == "llama3.2"

    def test_get_provider_anthropic(self):
        with patch("modelx_voice.brain.llm_client.AsyncAnthropic") as mock_client:
            provider = get_provider("anthropic", api_key="test-key")
            assert isinstance(provider, AnthropicProvider)

    def test_get_provider_openai(self):
        with patch("modelx_voice.brain.llm_client.AsyncOpenAI") as mock_client:
            provider = get_provider("openai", api_key="test-key")
            assert isinstance(provider, OpenAIProvider)

    def test_get_provider_ollama(self):
        provider = get_provider("ollama", base_url="http://localhost:11434")
        assert isinstance(provider, OllamaProvider)

    def test_get_provider_invalid(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("invalid_provider")


class TestAnthropicProvider:
    @pytest.fixture
    def provider(self):
        with patch("modelx_voice.brain.llm_client.AsyncAnthropic") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance
            provider = AnthropicProvider(api_key="test-key")
            provider._client = mock_instance
            yield provider

    @pytest.mark.asyncio
    async def test_chat_completion(self, provider):
        # Mock response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Test response")]
        mock_response.usage = MagicMock(input_tokens=10, output_tokens=20)
        mock_response.stop_reason = "end_turn"

        provider._client.messages.create = AsyncMock(return_value=mock_response)

        messages = [Message(role="user", content="Hello")]
        response = await provider.chat_completion(messages, "claude-sonnet-4")

        assert response.content == "Test response"
        assert response.usage["input_tokens"] == 10
        assert response.model == "claude-sonnet-4"

    @pytest.mark.asyncio
    async def test_stream_chat_completion(self, provider):
        # Mock streaming response
        async def mock_stream(*args, **kwargs):
            class MockStream:
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *args):
                    pass
                async def text_stream(self):
                    yield "Hello"
                    yield " "
                    yield "world"
            return MockStream()

        provider._client.messages.stream = mock_stream

        messages = [Message(role="user", content="Hello")]
        chunks = []
        async for chunk in provider.stream_chat_completion(messages, "test-model"):
            chunks.append(chunk)

        assert chunks == ["Hello", " ", "world"]


class TestOpenAIProvider:
    @pytest.fixture
    def provider(self):
        with patch("modelx_voice.brain.llm_client.AsyncOpenAI") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance
            provider = OpenAIProvider(api_key="test-key")
            provider._client = mock_instance
            yield provider

    @pytest.mark.asyncio
    async def test_chat_completion(self, provider):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20)
        mock_response.choices[0].finish_reason = "stop"

        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        messages = [Message(role="user", content="Hello")]
        response = await provider.chat_completion(messages, "gpt-4o")

        assert response.content == "Test response"
        assert response.usage["input_tokens"] == 10


class TestOllamaProvider:
    @pytest.fixture
    def provider(self):
        provider = OllamaProvider(base_url="http://localhost:11434")
        yield provider

    @pytest.mark.asyncio
    async def test_chat_completion(self, provider):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value={
            "message": {"content": "Test response"},
            "prompt_eval_count": 10,
            "eval_count": 20,
            "done_reason": "stop",
        })
        mock_response.raise_for_status = MagicMock()

        provider._client.post = AsyncMock(return_value=mock_response)

        messages = [Message(role="user", content="Hello")]
        response = await provider.chat_completion(messages, "llama3.2")

        assert response.content == "Test response"
        assert response.usage["input_tokens"] == 10

    @pytest.mark.asyncio
    async def test_stream_chat_completion(self, provider):
        # Mock streaming response
        lines = [
            '{"message": {"content": "Hello"}}',
            '{"message": {"content": " world"}}',
            '{"done": true}',
        ]

        async def mock_stream(*args, **kwargs):
            class MockStream:
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *args):
                    pass
                async def aiter_lines(self):
                    for line in lines:
                        yield line
            return MockStream()

        provider._client.stream = mock_stream

        messages = [Message(role="user", content="Hello")]
        chunks = []
        async for chunk in provider.stream_chat_completion(messages, "llama3.2"):
            chunks.append(chunk)

        assert chunks == ["Hello", " world"]