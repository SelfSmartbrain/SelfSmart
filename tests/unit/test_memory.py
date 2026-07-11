"""Tests for conversation memory."""
import pytest
import json
import time
from pathlib import Path
from unittest.mock import patch

from modelx_voice.brain.context import (
    ConversationMemory,
    ConversationExchange,
    ModelXBrain,
)


class TestConversationMemory:
    def setup_method(self):
        self.tmp_path = Path("/tmp/test_conversation.json")
        self.memory = ConversationMemory(
            max_turns=5,
            max_tokens=1000,
            persistence_file=self.tmp_path,
        )

    def teardown_method(self):
        if self.tmp_path.exists():
            self.tmp_path.unlink()

    def test_add_exchange(self):
        self.memory.add_exchange("Hello", "Hi there!")
        assert self.memory.turn_count == 1

        exchange = self.memory.get_full_history()[0]
        assert exchange.user == "Hello"
        assert exchange.assistant == "Hi there!"
        assert exchange.timestamp > 0

    def test_multiple_exchanges(self):
        for i in range(3):
            self.memory.add_exchange(f"User {i}", f"Assistant {i}")

        assert self.memory.turn_count == 3
        history = self.memory.get_full_history()
        assert len(history) == 3
        assert history[0].user == "User 0"
        assert history[2].user == "User 2"

    def test_get_context(self):
        self.memory.add_exchange("First", "Response 1")
        self.memory.add_exchange("Second", "Response 2")
        self.memory.add_exchange("Third", "Response 3")

        context = self.memory.get_context(recent_turns=2)
        assert len(context) == 4  # 2 turns * 2 messages each
        assert context[0].content == "Second"
        assert context[1].content == "Response 2"
        assert context[2].content == "Third"
        assert context[3].content == "Response 3"

    def test_max_turns_pruning(self):
        for i in range(7):  # More than max_turns=5
            self.memory.add_exchange(f"User {i}", f"Assistant {i}")

        assert self.memory.turn_count == 5
        history = self.memory.get_full_history()
        assert history[0].user == "User 2"  # First 2 pruned
        assert history[-1].user == "User 6"

    def test_token_pruning(self):
        # Add exchanges with token counts
        for i in range(4):
            self.memory.add_exchange(
                f"User {i}",
                f"Assistant {i}",
                tokens_used={"input_tokens": 300, "output_tokens": 300}
            )

        # Total: 4 * 600 = 2400 tokens, exceeds max_tokens=1000
        # Should prune oldest until under budget
        assert self.memory.turn_count <= 3  # At most 3 turns (1800) or 2 (1200)
        assert self.memory.estimated_tokens <= 1000

    def test_clear(self):
        self.memory.add_exchange("Hello", "Hi")
        self.memory.clear()
        assert self.memory.turn_count == 0
        assert self.memory.estimated_tokens == 0
        assert not self.tmp_path.exists()

    def test_persistence(self):
        self.memory.add_exchange("Hello", "Hi", tokens_used={"input_tokens": 10, "output_tokens": 20})
        self.memory.save()

        # Load into new memory instance
        memory2 = ConversationMemory(persistence_file=self.tmp_path)
        assert memory2.turn_count == 1
        assert memory2.estimated_tokens == 30

        exchange = memory2.get_full_history()[0]
        assert exchange.user == "Hello"
        assert exchange.assistant == "Hi"

    def test_export_conversation(self):
        self.memory.add_exchange("Q1", "A1")
        self.memory.add_exchange("Q2", "A2")

        export_path = Path("/tmp/export.json")
        self.memory.export_conversation(export_path)

        with open(export_path) as f:
            data = json.load(f)

        assert "exported_at" in data
        assert len(data["exchanges"]) == 2
        assert data["total_tokens"] == 0
        export_path.unlink()

    def test_empty_context(self):
        context = self.memory.get_context()
        assert context == []

    def test_estimated_tokens_property(self):
        assert self.memory.estimated_tokens == 0
        self.memory.add_exchange("Hello", "Hi", tokens_used={"input_tokens": 100, "output_tokens": 200})
        assert self.memory.estimated_tokens == 300