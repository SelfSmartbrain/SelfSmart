"""
Shared agent state for the LangGraph workflow.

This module defines the TypedDict that flows through all nodes in the
orchestrator's state graph. Each agent reads from and writes to this
shared state to coordinate the multi-agent workflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Any, Literal

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

# ---------------------------------------------------------------------------
# Data classes for structured task and result tracking
# ---------------------------------------------------------------------------


@dataclass
class TaskSpec:
    """Specification for a decomposed task."""

    id: str
    title: str
    description: str
    agent_type: Literal["research", "execution", "memory"]
    priority: int = 1  # 1 = highest
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Result of a completed task."""

    task_id: str
    status: Literal["completed", "failed", "partial"]
    output: Any = None
    error: str | None = None
    tokens_used: int = 0
    duration_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorRecord:
    """Record of an error that occurred during execution."""

    task_id: str | None
    agent_type: str
    error_type: str
    message: str
    recoverable: bool = True
    retry_count: int = 0


@dataclass
class MemoryRecord:
    """A recalled memory item."""

    id: str
    content: str
    memory_type: str
    importance_score: float
    relevance_score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeChunk:
    """A retrieved knowledge chunk."""

    chunk_id: str
    content: str
    score: float
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReflectionOutput:
    """Output from the reflection agent."""

    successes: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    root_causes: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    should_retry: bool = False
    retry_strategy: str | None = None


# ---------------------------------------------------------------------------
# Shared agent state — flows through the LangGraph StateGraph
# ---------------------------------------------------------------------------


class _AgentStatePlaceholder:
    """
    Legacy placeholder — see AgentStateDict below for the real state schema.

    This class existed as documentation-only. The actual AgentState alias
    is created after AgentStateDict is defined (end of this module).
    """

    pass


# We use a TypedDict annotation dict for LangGraph's StateGraph.
# This is the canonical way to define state in LangGraph.
from typing import TypedDict


class AgentStateDict(TypedDict, total=False):
    """TypedDict state for LangGraph StateGraph."""

    # Goal & Planning
    goal: str
    goal_analysis: dict[str, Any] | None
    task_plan: list[dict[str, Any]]
    current_task_index: int

    # Execution
    messages: Annotated[list[BaseMessage], add_messages]
    task_results: dict[str, dict[str, Any]]
    errors: list[dict[str, Any]]

    # Memory & Knowledge
    retrieved_memories: list[dict[str, Any]]
    retrieved_knowledge: list[dict[str, Any]]

    # Reflection
    reflection: dict[str, Any] | None

    # Control Flow
    session_id: str
    user_id: str
    iteration_count: int
    max_iterations: int
    status: str  # "planning" | "executing" | "reflecting" | "complete" | "failed"
    next_agent: str | None

    # Meta-Learning (Phase 5)
    task_classification: dict[str, Any] | None
    selected_strategy: dict[str, Any] | None
    strategy_executions: dict[str, dict[str, Any]]
    experience_context: str | None
    learnings: list[dict[str, Any]]
    replan_count: int

    # Autonomous Research (Phase 6)
    knowledge_gaps: list[dict[str, Any]]
    generated_goals: list[dict[str, Any]]
    research_tracks: list[dict[str, Any]]
    portfolio_summary: dict[str, Any] | None

    # Self-Improving Intelligence (Phase 7)
    cognition_reflections: list[dict[str, Any]]
    failure_patterns: list[dict[str, Any]]
    research_strategies: list[dict[str, Any]]
    cognitive_skills: list[dict[str, Any]]
    cognitive_metrics: list[dict[str, Any]]
    autonomy_score: float
    learning_velocity: float
    best_strategy: dict[str, Any] | None
    optimization_recommendations: list[str]

    # World Model (Phase 9)
    hypotheses: list[dict[str, Any]]
    beliefs: list[dict[str, Any]]
    experiment_results: list[dict[str, Any]]
    patterns: list[dict[str, Any]]
    causal_links: list[dict[str, Any]]
    experiments: list[dict[str, Any]]

    # Project Execution (Phase 12)
    project: dict[str, Any] | None
    opportunities: list[dict[str, Any]]
    tasks: list[dict[str, Any]]

    # Evolution (Phase 10G)
    genome_data: dict[str, Any]

    # Output
    final_report: str | None


AgentState = AgentStateDict  # type: ignore[misc]


def create_initial_state(
    goal: str,
    user_id: str,
    session_id: str,
    max_iterations: int = 20,
) -> AgentStateDict:
    """
    Create the initial state for a new goal execution.

    Args:
        goal: The high-level user goal.
        user_id: User identifier.
        session_id: Database session identifier.
        max_iterations: Maximum agent loop iterations.

    Returns:
        Initialized AgentStateDict ready for the LangGraph workflow.
    """
    return AgentStateDict(
        goal=goal,
        goal_analysis=None,
        task_plan=[],
        current_task_index=0,
        messages=[],
        task_results={},
        errors=[],
        retrieved_memories=[],
        retrieved_knowledge=[],
        reflection=None,
        session_id=session_id,
        user_id=user_id,
        iteration_count=0,
        max_iterations=max_iterations,
        status="planning",
        next_agent=None,
        task_classification=None,
        selected_strategy=None,
        strategy_executions={},
        experience_context=None,
        learnings=[],
        replan_count=0,
        knowledge_gaps=[],
        generated_goals=[],
        research_tracks=[],
        portfolio_summary=None,
        cognition_reflections=[],
        failure_patterns=[],
        research_strategies=[],
        cognitive_skills=[],
        cognitive_metrics=[],
        autonomy_score=0.0,
        learning_velocity=0.0,
        best_strategy=None,
        optimization_recommendations=[],
        # World Model (Phase 9)
        hypotheses=[],
        beliefs=[],
        experiment_results=[],
        patterns=[],
        causal_links=[],
        experiments=[],
        # Project Execution (Phase 12)
        project=None,
        opportunities=[],
        tasks=[],
        # Evolution (Phase 10G)
        genome_data={},
        # Output
        final_report=None,
    )


# ---------------------------------------------------------------------------
# Backward-compatible alias: AgentState → AgentStateDict
# Existing code that imports AgentState now gets the real TypedDict schema.
# ---------------------------------------------------------------------------
AgentState = AgentStateDict  # type: ignore[misc]
