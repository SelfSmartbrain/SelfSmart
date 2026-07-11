"""Integration tests for the audio pipeline."""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from modelx_voice.pipeline import AudioPipeline, PipelineConfig, PipelineState
from modelx_voice.config import ConfigManager
from modelx_voice.brain import ModelXBrain, ConversationMemory
from modelx_voice.ui import SimpleVoiceUI


class TestAudioPipeline:
    @pytest.fixture
    def config_manager(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            cm = ConfigManager(config_file=config_file)
            # Configure for testing
            with patch("keyring.set_password"):
                cm.update_api(provider="ollama", api_key="", base_url="http://localhost:11434", model="llama3.2")
            yield cm

    @pytest.fixture
    def brain(self, config_manager):
        config = config_manager.load()
        memory = ConversationMemory()
        brain = ModelXBrain(
            provider=config.api.provider,
            api_key=config.api.api_key,
            base_url=config.api.base_url,
            model=config.api.model,
            memory=memory,
        )
        yield brain

    @pytest.fixture
    def pipeline_config(self, config_manager):
        config = config_manager.load()
        return PipelineConfig(
            sample_rate=config.audio.sample_rate,
            vad_aggressiveness=config.behavior.vad_aggressiveness,
            whisper_model="tiny",  # Fast for tests
            voice_profile=config.voice.selected_voice,
            auto_listen=config.behavior.auto_listen,
        )

    @pytest.fixture
    def ui(self):
        return SimpleVoiceUI()

    @pytest.mark.asyncio
    async def test_pipeline_initialization(self, pipeline_config, config_manager, brain, ui):
        pipeline = AudioPipeline(pipeline_config, config_manager, brain, ui)

        with patch("modelx_voice.pipeline.AudioCapture") as mock_capture, \
             patch("modelx_voice.pipeline.AudioPlayback") as mock_playback, \
             patch("modelx_voice.pipeline.StreamingVAD"), \
             patch("modelx_voice.pipeline.WhisperTranscriber"), \
             patch("modelx_voice.pipeline.PiperSynthesizer"):

            # Setup mocks
            mock_capture_instance = AsyncMock()
            mock_capture.return_value = mock_capture_instance
            mock_playback_instance = AsyncMock()
            mock_playback.return_value = mock_playback_instance

            await pipeline.initialize()

            assert pipeline.state == PipelineState.IDLE
            assert pipeline._capture is not None
            assert pipeline._playback is not None
            mock_capture_instance.start.assert_called_once()
            mock_playback_instance.start.assert_called_once()

            await pipeline.cleanup()
            mock_capture_instance.stop.assert_called_once()
            mock_playback_instance.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_state_transitions(self, pipeline_config, config_manager, brain, ui):
        pipeline = AudioPipeline(pipeline_config, config_manager, brain, ui)

        with patch("modelx_voice.pipeline.AudioCapture"), \
             patch("modelx_voice.pipeline.AudioPlayback"), \
             patch("modelx_voice.pipeline.StreamingVAD"), \
             patch("modelx_voice.pipeline.WhisperTranscriber"), \
             patch("modelx_voice.pipeline.PiperSynthesizer"):

            await pipeline.initialize()
            assert pipeline.state == PipelineState.IDLE

            # Test state property
            assert isinstance(pipeline.state, PipelineState)


class TestConversationMemoryIntegration:
    @pytest.mark.asyncio
    async def test_memory_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            persist_file = Path(tmpdir) / "conversation.json"
            memory = ConversationMemory(persistence_file=persist_file)

            memory.add_exchange("Hello", "Hi there!", {"input_tokens": 5, "output_tokens": 10})
            memory.add_exchange("How are you?", "I'm good!", {"input_tokens": 8, "output_tokens": 12})

            assert memory.turn_count == 2
            assert memory.total_tokens == 35

            # Create new memory instance with same file
            memory2 = ConversationMemory(persistence_file=persist_file)
            assert memory2.turn_count == 2
            assert memory2.total_tokens == 35

            context = memory2.get_context(recent_turns=2)
            assert len(context) == 4  # 2 turns = 4 messages
            assert context[0].content == "Hello"
            assert context[1].content == "Hi there!"

    @pytest.mark.asyncio
    async def test_token_pruning(self):
        memory = ConversationMemory(max_tokens=50)
        
        # Add exchanges with known token counts
        for i in range(10):
            memory.add_exchange(
                f"User {i}", 
                f"Assistant {i}", 
                {"input_tokens": 10, "output_tokens": 10}
            )

        # Should have pruned to stay under 50 tokens
        # Each exchange = 20 tokens, so max 2 exchanges (40 tokens)
        assert memory.total_tokens <= 50
        assert memory.turn_count <= 3  # Some buffer


class TestModelXBrainIntegration:
    @pytest.fixture
    def brain(self):
        memory = ConversationMemory()
        brain = ModelXBrain(
            provider="ollama",
            base_url="http://localhost:11434",
            model="llama3.2",
            memory=memory,
        )
        yield brain

    @pytest.mark.asyncio
    async def test_brain_initialization(self, brain):
        assert brain.provider_name == "ollama"
        assert brain.model == "llama3.2"
        assert brain.memory is not None
        assert "You are ModelX" in brain.system_prompt

    @pytest.mark.asyncio
    async def test_clear_memory(self, brain):
        brain.memory.add_exchange("Test", "Response")
        assert brain.memory.turn_count == 1

        brain.clear_memory()
        assert brain.memory.turn_count == 0

    @pytest.mark.asyncio
    async def test_get_stats(self, brain):
        stats = brain.get_stats()
        assert stats["provider"] == "ollama"
        assert stats["model"] == "llama3.2"
        assert stats["turns"] == 0
        assert stats["total_tokens"] == 0

    @pytest.mark.asyncio
    async def test_set_system_prompt(self, brain):
        brain.set_system_prompt("Custom prompt")
        assert brain.system_prompt == "Custom prompt"

    @pytest.mark.asyncio
    async def test_close(self, brain):
        # Should not raise
        await brain.close()