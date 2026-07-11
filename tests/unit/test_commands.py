"""Tests for voice command processor."""
import pytest
from modelx_voice.ui.commands import (
    CommandProcessor,
    VoiceCommand,
    CommandType,
)


class TestCommandProcessor:
    def setup_method(self):
        self.processor = CommandProcessor()

    # Stop commands
    @pytest.mark.parametrize("text", [
        "stop",
        "quit",
        "exit",
        "goodbye",
        "bye",
        "stop listening",
    ])
    def test_stop_commands(self, text):
        cmd = self.processor.process(text)
        assert cmd.type == CommandType.STOP
        assert cmd.raw_text == text

    # Pause commands
    @pytest.mark.parametrize("text", [
        "pause",
        "wait",
        "hold on",
    ])
    def test_pause_commands(self, text):
        cmd = self.processor.process(text)
        assert cmd.type == CommandType.PAUSE

    # Clear commands
    @pytest.mark.parametrize("text", [
        "clear",
        "clear history",
        "reset",
        "forget",
        "clear conversation",
    ])
    def test_clear_commands(self, text):
        cmd = self.processor.process(text)
        assert cmd.type == CommandType.CLEAR

    # Save commands
    @pytest.mark.parametrize("text", [
        "save",
        "save conversation",
        "export",
    ])
    def test_save_commands(self, text):
        cmd = self.processor.process(text)
        assert cmd.type == CommandType.SAVE

    # Help commands
    @pytest.mark.parametrize("text", [
        "help",
        "commands",
        "what can you do",
    ])
    def test_help_commands(self, text):
        cmd = self.processor.process(text)
        assert cmd.type == CommandType.HELP

    # Switch voice commands
    @pytest.mark.parametrize("text,expected_voice", [
        ("switch voice professional", "professional"),
        ("switch voice casual", "casual"),
        ("switch voice clear", "clear"),
        ("change voice professional", "professional"),
        ("use voice casual", "casual"),
        ("voice clear", "clear"),
        ("voice pro", "professional"),
        ("voice friendly", "casual"),
        ("voice male", "professional"),
        ("voice female", "casual"),
    ])
    def test_switch_voice_commands(self, text, expected_voice):
        cmd = self.processor.process(text)
        assert cmd.type == CommandType.SWITCH_VOICE
        assert cmd.args.get("voice") == expected_voice

    # Status commands
    @pytest.mark.parametrize("text", [
        "status",
        "stats",
        "info",
    ])
    def test_status_commands(self, text):
        cmd = self.processor.process(text)
        assert cmd.type == CommandType.STATUS

    # Repeat commands
    @pytest.mark.parametrize("text", [
        "repeat",
        "say that again",
        "say again",
    ])
    def test_repeat_commands(self, text):
        cmd = self.processor.process(text)
        assert cmd.type == CommandType.REPEAT

    # Non-commands
    @pytest.mark.parametrize("text", [
        "hello world",
        "what is the weather",
        "tell me a joke",
        "how are you",
        "stop talking about that",
    ])
    def test_non_commands(self, text):
        cmd = self.processor.process(text)
        assert cmd.type == CommandType.NONE

    # Case insensitivity
    def test_case_insensitive(self):
        assert self.processor.process("STOP").type == CommandType.STOP
        assert self.processor.process("Stop").type == CommandType.STOP
        assert self.processor.process("sToP").type == CommandType.STOP

    # Punctuation handling
    def test_punctuation_handling(self):
        assert self.processor.process("stop.").type == CommandType.STOP
        assert self.processor.process("stop!").type == CommandType.STOP
        assert self.processor.process("stop?").type == CommandType.STOP
        assert self.processor.process("clear...").type == CommandType.CLEAR

    # Whitespace handling
    def test_whitespace_handling(self):
        assert self.processor.process("  stop  ").type == CommandType.STOP
        assert self.processor.process("\tstop\n").type == CommandType.STOP

    # Help text
    def test_help_text(self):
        help_text = self.processor.get_help_text()
        assert "stop" in help_text.lower()
        assert "clear" in help_text.lower()
        assert "switch voice" in help_text.lower()
        assert "status" in help_text.lower()

    # Last response
    def test_last_response(self):
        assert self.processor.get_last_response() == ""
        self.processor.set_last_response("Hello world")
        assert self.processor.get_last_response() == "Hello world"