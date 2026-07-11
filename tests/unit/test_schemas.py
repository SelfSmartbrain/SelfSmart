"""Tests for API Pydantic schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.api.schemas.goals import GoalCreate, GoalExecute, GoalResponse, Priority
from src.api.schemas.memory import MemoryCreate, MemoryRecall, MemoryType
from src.api.schemas.knowledge import KnowledgeIngest, KnowledgeSearch, SourceType


# =========================================================================
# GoalCreate
# =========================================================================


class TestGoalCreate:
    """Tests for GoalCreate schema validation."""

    def test_valid_minimal(self):
        """Minimal valid goal with just the required field."""
        goal = GoalCreate(goal="Research the latest advances in AI safety")
        assert goal.goal == "Research the latest advances in AI safety"
        assert goal.context is None
        assert goal.priority == Priority.NORMAL
        assert goal.max_iterations == 20

    def test_valid_full(self):
        """Goal with all fields specified."""
        goal = GoalCreate(
            goal="Analyze transformer architectures for text generation",
            context="Focus on efficiency improvements since 2023",
            priority=Priority.HIGH,
            max_iterations=50,
        )
        assert goal.priority == Priority.HIGH
        assert goal.max_iterations == 50
        assert goal.context is not None

    def test_goal_min_length_violation(self):
        """Goal shorter than 10 characters should fail."""
        with pytest.raises(ValidationError) as exc_info:
            GoalCreate(goal="short")
        errors = exc_info.value.errors()
        assert any(e["type"] == "string_too_short" for e in errors)

    def test_goal_max_length_violation(self):
        """Goal longer than 5000 characters should fail."""
        with pytest.raises(ValidationError):
            GoalCreate(goal="x" * 5001)

    def test_max_iterations_below_minimum(self):
        """max_iterations < 1 should fail."""
        with pytest.raises(ValidationError):
            GoalCreate(goal="A valid goal description here", max_iterations=0)

    def test_max_iterations_above_maximum(self):
        """max_iterations > 100 should fail."""
        with pytest.raises(ValidationError):
            GoalCreate(goal="A valid goal description here", max_iterations=101)

    def test_priority_values(self):
        """All priority enum values should be accepted."""
        for p in Priority:
            goal = GoalCreate(goal="A valid goal description here", priority=p)
            assert goal.priority == p

    def test_serialization_round_trip(self):
        """Model should serialize to dict and back."""
        original = GoalCreate(
            goal="Analyze transformer architectures and write a report",
            context="Include attention mechanisms",
            priority=Priority.CRITICAL,
            max_iterations=75,
        )
        data = original.model_dump()
        restored = GoalCreate(**data)
        assert restored == original

    def test_json_serialization(self):
        """Model should serialize to JSON and deserialize."""
        original = GoalCreate(goal="Test goal for JSON serialization")
        json_str = original.model_dump_json()
        restored = GoalCreate.model_validate_json(json_str)
        assert restored.goal == original.goal


# =========================================================================
# GoalExecute
# =========================================================================


class TestGoalExecute:
    """Tests for GoalExecute schema."""

    def test_defaults(self):
        goal_exec = GoalExecute()
        assert goal_exec.resume is False
        assert goal_exec.override_max_iterations is None

    def test_override_iterations_valid(self):
        goal_exec = GoalExecute(override_max_iterations=50)
        assert goal_exec.override_max_iterations == 50

    def test_override_iterations_below_min(self):
        with pytest.raises(ValidationError):
            GoalExecute(override_max_iterations=0)

    def test_override_iterations_above_max(self):
        with pytest.raises(ValidationError):
            GoalExecute(override_max_iterations=101)


# =========================================================================
# MemoryCreate
# =========================================================================


class TestMemoryCreate:
    """Tests for MemoryCreate schema validation."""

    def test_valid_minimal(self):
        mem = MemoryCreate(content="A simple memory")
        assert mem.content == "A simple memory"
        assert mem.memory_type == MemoryType.SEMANTIC
        assert mem.importance_score == 0.5
        assert mem.metadata == {}

    def test_valid_full(self):
        mem = MemoryCreate(
            content="Episodic memory content",
            memory_type=MemoryType.EPISODIC,
            metadata={"source": "test"},
            importance_score=0.9,
        )
        assert mem.memory_type == MemoryType.EPISODIC
        assert mem.importance_score == 0.9

    def test_empty_content_fails(self):
        with pytest.raises(ValidationError):
            MemoryCreate(content="")

    def test_importance_below_zero(self):
        with pytest.raises(ValidationError):
            MemoryCreate(content="test", importance_score=-0.1)

    def test_importance_above_one(self):
        with pytest.raises(ValidationError):
            MemoryCreate(content="test", importance_score=1.1)

    def test_importance_boundary_values(self):
        """Boundary values 0.0 and 1.0 should be accepted."""
        low = MemoryCreate(content="test", importance_score=0.0)
        high = MemoryCreate(content="test", importance_score=1.0)
        assert low.importance_score == 0.0
        assert high.importance_score == 1.0

    def test_all_memory_types(self):
        for mt in MemoryType:
            mem = MemoryCreate(content="test", memory_type=mt)
            assert mem.memory_type == mt

    def test_serialization_round_trip(self):
        original = MemoryCreate(
            content="Important fact to remember",
            memory_type=MemoryType.PROCEDURAL,
            importance_score=0.8,
            metadata={"key": "value"},
        )
        data = original.model_dump()
        restored = MemoryCreate(**data)
        assert restored == original


# =========================================================================
# MemoryRecall
# =========================================================================


class TestMemoryRecall:
    """Tests for MemoryRecall schema."""

    def test_valid_minimal(self):
        recall = MemoryRecall(query="search term")
        assert recall.query == "search term"
        assert recall.memory_type is None
        assert recall.limit == 10
        assert recall.min_importance == 0.0

    def test_valid_full(self):
        recall = MemoryRecall(
            query="something",
            memory_type=MemoryType.PROCEDURAL,
            limit=25,
            min_importance=0.5,
        )
        assert recall.limit == 25
        assert recall.memory_type == MemoryType.PROCEDURAL

    def test_empty_query_fails(self):
        with pytest.raises(ValidationError):
            MemoryRecall(query="")

    def test_limit_below_min(self):
        with pytest.raises(ValidationError):
            MemoryRecall(query="test", limit=0)

    def test_limit_above_max(self):
        with pytest.raises(ValidationError):
            MemoryRecall(query="test", limit=51)

    def test_min_importance_range(self):
        with pytest.raises(ValidationError):
            MemoryRecall(query="test", min_importance=-0.1)
        with pytest.raises(ValidationError):
            MemoryRecall(query="test", min_importance=1.1)


# =========================================================================
# KnowledgeIngest
# =========================================================================


class TestKnowledgeIngest:
    """Tests for KnowledgeIngest schema."""

    def test_valid_with_content(self):
        ki = KnowledgeIngest(title="Doc Title", content="Some content")
        assert ki.content == "Some content"
        assert ki.url is None

    def test_valid_with_url(self):
        ki = KnowledgeIngest(title="Doc Title", url="https://example.com")
        assert ki.url == "https://example.com"
        assert ki.content is None

    def test_valid_with_both(self):
        ki = KnowledgeIngest(title="Title", content="text", url="https://example.com")
        assert ki.content == "text"
        assert ki.url == "https://example.com"

    def test_neither_content_nor_url_fails(self):
        """Must provide at least content or url."""
        with pytest.raises(ValueError, match="Either 'content' or 'url' must be provided"):
            KnowledgeIngest(title="Title")

    def test_source_type_default(self):
        ki = KnowledgeIngest(title="T", content="C")
        assert ki.source_type == SourceType.MANUAL

    def test_all_source_types(self):
        for st in SourceType:
            ki = KnowledgeIngest(title="T", content="C", source_type=st)
            assert ki.source_type == st

    def test_empty_title_fails(self):
        with pytest.raises(ValidationError):
            KnowledgeIngest(title="", content="content")

    def test_serialization_round_trip(self):
        original = KnowledgeIngest(
            title="Test Document",
            content="Document content here",
            source_type=SourceType.MANUAL,
            metadata={"key": "value"},
        )
        data = original.model_dump()
        restored = KnowledgeIngest(**data)
        assert restored == original


# =========================================================================
# KnowledgeSearch
# =========================================================================


class TestKnowledgeSearch:
    """Tests for KnowledgeSearch schema."""

    def test_valid_minimal(self):
        ks = KnowledgeSearch(query="transformers")
        assert ks.query == "transformers"
        assert ks.limit == 10
        assert ks.score_threshold == 0.5
        assert ks.source_type is None

    def test_valid_full(self):
        ks = KnowledgeSearch(
            query="attention mechanism",
            source_type=SourceType.ARXIV,
            limit=20,
            score_threshold=0.8,
        )
        assert ks.source_type == SourceType.ARXIV
        assert ks.limit == 20

    def test_empty_query_fails(self):
        with pytest.raises(ValidationError):
            KnowledgeSearch(query="")

    def test_score_threshold_below_zero(self):
        with pytest.raises(ValidationError):
            KnowledgeSearch(query="test", score_threshold=-0.1)

    def test_score_threshold_above_one(self):
        with pytest.raises(ValidationError):
            KnowledgeSearch(query="test", score_threshold=1.1)

    def test_limit_below_min(self):
        with pytest.raises(ValidationError):
            KnowledgeSearch(query="test", limit=0)

    def test_limit_above_max(self):
        with pytest.raises(ValidationError):
            KnowledgeSearch(query="test", limit=51)

    def test_serialization(self):
        original = KnowledgeSearch(query="test query", limit=5)
        data = original.model_dump()
        restored = KnowledgeSearch(**data)
        assert restored == original

    def test_json_round_trip(self):
        original = KnowledgeSearch(query="json test", score_threshold=0.7)
        json_str = original.model_dump_json()
        restored = KnowledgeSearch.model_validate_json(json_str)
        assert restored.query == original.query
        assert restored.score_threshold == original.score_threshold
