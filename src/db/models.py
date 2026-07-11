"""
SQLAlchemy 2.0 ORM models for the Autonomous Agent Platform.

All models use:
- ``Mapped[]`` type annotations (SQLAlchemy 2.0 style).
- UUID v7 primary keys via ``uuid6.uuid7()`` for time-ordered IDs.
- Proper indexes for query performance on hot paths.
- Relationships with ``back_populates`` for bidirectional traversal.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import uuid6
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

from src.db.enums import (
    ExecutionStatus,
    MemoryType,
    Priority,
    ReflectionType,
    SessionStatus,
    SourceType,
    TaskStatus,
    TaskType,
    StrategyStatus,
    MetricType,
    SkillStatus,
    ResearchTrackStatus,
    PortfolioStatus,
    GoalStatus,
    FailureSeverity,
    CognitiveMetricType,
    CognitiveState,
    AttentionLevel,
    ReasoningMode,
    SocietyStatus,
    AgentStatus,
    MissionStatus,
    GoalStatus as MissionGoalStatus,
    ProgramStatus,
    TaskMarketStatus,
    ObjectiveStatus,
)


def _generate_uuid7() -> UUID:
    """Generate a UUID v7 (time-ordered) for use as a primary key."""
    return uuid6.uuid7()


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models.

    Provides a ``type_annotation_map`` so that ``Mapped[dict[str, Any]]``
    automatically resolves to PostgreSQL JSONB.
    """

    type_annotation_map = {
        dict[str, Any]: JSONB,
    }


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


class User(Base):
    """Platform user who owns sessions and memories."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=_generate_uuid7,
    )
    email: Mapped[str] = mapped_column(
        String(320), unique=True, nullable=False, index=True
    )
    api_key_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False, server_default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    sessions: Mapped[list[Session]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    memories: Mapped[list[Memory]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!s} email={self.email!r}>"


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


class Session(Base):
    """A goal-driven agent session owned by a user."""

    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_user_status", "user_id", "status"),
        Index("ix_sessions_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=_generate_uuid7,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status", create_constraint=True),
        nullable=False,
        default=SessionStatus.PENDING,
        index=True,
    )
    context: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped[User] = relationship(back_populates="sessions")
    tasks: Mapped[list[Task]] = relationship(
        back_populates="session", cascade="all, delete-orphan", lazy="selectin"
    )
    agent_logs: Mapped[list[AgentLog]] = relationship(
        back_populates="session", cascade="all, delete-orphan", lazy="selectin"
    )
    memories: Mapped[list[Memory]] = relationship(
        back_populates="session", cascade="all, delete-orphan", lazy="selectin"
    )
    reflections: Mapped[list[ReflectionRecord]] = relationship(
        back_populates="session", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Session id={self.id!s} status={self.status.value!r}>"


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


class Task(Base):
    """An individual unit of work within a session, supporting hierarchy."""

    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_session_status", "session_id", "status"),
        Index("ix_tasks_status_priority", "status", "priority"),
        Index("ix_tasks_parent", "parent_task_id"),
        Index("ix_tasks_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=_generate_uuid7,
    )
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", create_constraint=True),
        nullable=False,
        default=TaskStatus.PENDING,
        index=True,
    )
    priority: Mapped[Priority] = mapped_column(
        Enum(Priority, name="priority", create_constraint=True),
        nullable=False,
        default=Priority.NORMAL,
    )
    agent_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dependencies: Mapped[list[UUID] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    session: Mapped[Session] = relationship(back_populates="tasks")
    parent_task: Mapped[Task | None] = relationship(
        back_populates="subtasks", remote_side=[id]
    )
    subtasks: Mapped[list[Task]] = relationship(
        back_populates="parent_task", cascade="all, delete-orphan"
    )
    executions: Mapped[list[Execution]] = relationship(
        back_populates="task", cascade="all, delete-orphan", lazy="selectin"
    )
    agent_logs: Mapped[list[AgentLog]] = relationship(
        back_populates="task", cascade="all, delete-orphan", lazy="selectin"
    )
    reflections: Mapped[list[ReflectionRecord]] = relationship(
        back_populates="task", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Task id={self.id!s} title={self.title!r} status={self.status.value!r}>"


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


class Execution(Base):
    """Record of a single agent execution attempt for a task."""

    __tablename__ = "executions"
    __table_args__ = (
        Index("ix_executions_task_id", "task_id"),
        Index("ix_executions_status", "status"),
        Index("ix_executions_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=_generate_uuid7,
    )
    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    agent_type: Mapped[str] = mapped_column(String(100), nullable=False)
    input_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[ExecutionStatus] = mapped_column(
        Enum(ExecutionStatus, name="execution_status", create_constraint=True),
        nullable=False,
        default=ExecutionStatus.RUNNING,
    )
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    task: Mapped[Task] = relationship(back_populates="executions")

    def __repr__(self) -> str:
        return f"<Execution id={self.id!s} task={self.task_id!s} status={self.status.value!r}>"


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------


class Memory(Base):
    """A memory entry in the agent's memory subsystem."""

    __tablename__ = "memories"
    __table_args__ = (
        Index("ix_memories_user_type", "user_id", "memory_type"),
        Index("ix_memories_session", "session_id"),
        Index("ix_memories_importance", "importance_score"),
        Index("ix_memories_last_accessed", "last_accessed"),
        Index("ix_memories_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=_generate_uuid7,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    memory_type: Mapped[MemoryType] = mapped_column(
        Enum(MemoryType, name="memory_type", create_constraint=True),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    importance_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5
    )
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_accessed: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped[User] = relationship(back_populates="memories")
    session: Mapped[Session | None] = relationship(back_populates="memories")

    def __repr__(self) -> str:
        return (
            f"<Memory id={self.id!s} type={self.memory_type.value!r} "
            f"importance={self.importance_score:.2f}>"
        )


# ---------------------------------------------------------------------------
# Knowledge Document & Chunk
# ---------------------------------------------------------------------------


class KnowledgeDocument(Base):
    """A source document ingested into the knowledge base."""

    __tablename__ = "knowledge_documents"
    __table_args__ = (
        Index("ix_kdocs_source_type", "source_type"),
        Index("ix_kdocs_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=_generate_uuid7,
    )
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    source: Mapped[str] = mapped_column(String(2000), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type", create_constraint=True),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    chunks: Mapped[list[KnowledgeChunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<KnowledgeDocument id={self.id!s} title={self.title!r}>"


class KnowledgeChunk(Base):
    """A chunked segment of a knowledge document, linked to an embedding."""

    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        Index("ix_kchunks_document", "document_id"),
        Index("ix_kchunks_document_index", "document_id", "chunk_index", unique=True),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=_generate_uuid7,
    )
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")

    def __repr__(self) -> str:
        return (
            f"<KnowledgeChunk id={self.id!s} doc={self.document_id!s} "
            f"index={self.chunk_index}>"
        )


# ---------------------------------------------------------------------------
# Agent Log
# ---------------------------------------------------------------------------


class AgentLog(Base):
    """Audit log entry for agent actions within a session."""

    __tablename__ = "agent_logs"
    __table_args__ = (
        Index("ix_agent_logs_session", "session_id"),
        Index("ix_agent_logs_task", "task_id"),
        Index("ix_agent_logs_agent_type", "agent_type"),
        Index("ix_agent_logs_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=_generate_uuid7,
    )
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    agent_type: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(200), nullable=False)
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    session: Mapped[Session] = relationship(back_populates="agent_logs")
    task: Mapped[Task | None] = relationship(back_populates="agent_logs")

    def __repr__(self) -> str:
        return (
            f"<AgentLog id={self.id!s} agent={self.agent_type!r} "
            f"action={self.action!r}>"
        )


# ---------------------------------------------------------------------------
# Reflection Record
# ---------------------------------------------------------------------------


class ReflectionRecord(Base):
    """Record of agent self-reflection for continuous improvement."""

    __tablename__ = "reflection_records"
    __table_args__ = (
        Index("ix_reflections_session", "session_id"),
        Index("ix_reflections_type", "reflection_type"),
        Index("ix_reflections_applied", "applied"),
        Index("ix_reflections_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=_generate_uuid7,
    )
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    reflection_type: Mapped[ReflectionType] = mapped_column(
        Enum(ReflectionType, name="reflection_type", create_constraint=True),
        nullable=False,
    )
    successes: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True
    )
    failures: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True
    )
    root_causes: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True
    )
    improvements: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True
    )
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5
    )
    applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    session: Mapped[Session] = relationship(back_populates="reflections")
    task: Mapped[Task | None] = relationship(back_populates="reflections")

    def __repr__(self) -> str:
        return (
            f"<ReflectionRecord id={self.id!s} type={self.reflection_type.value!r} "
            f"applied={self.applied}>"
        )


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------


class Strategy(Base):
    """A learned strategy for executing a specific type of task."""

    __tablename__ = "strategies"
    __table_args__ = (
        Index("ix_strategies_task_type", "task_type"),
        Index("ix_strategies_status", "status"),
        Index("ix_strategies_is_global", "is_global"),
        Index("ix_strategies_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    task_type: Mapped[TaskType] = mapped_column(
        Enum(TaskType, name="task_type", create_constraint=True),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    source_session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    success_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[StrategyStatus] = mapped_column(
        Enum(StrategyStatus, name="strategy_status", create_constraint=True),
        nullable=False,
        default=StrategyStatus.TESTING,
    )
    is_global: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    source_session: Mapped[Session | None] = relationship()
    executions: Mapped[list[StrategyExecution]] = relationship(
        back_populates="strategy", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Strategy id={self.id!s} name={self.name!r} type={self.task_type.value!r}>"


class StrategyExecution(Base):
    """Record of a strategy being applied to a task."""

    __tablename__ = "strategy_executions"
    __table_args__ = (
        Index("ix_strategy_executions_strategy", "strategy_id"),
        Index("ix_strategy_executions_session", "session_id"),
        Index("ix_strategy_executions_task", "task_id"),
        Index("ix_strategy_executions_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    strategy: Mapped[Strategy] = relationship(back_populates="executions")
    session: Mapped[Session] = relationship()
    task: Mapped[Task] = relationship()

    def __repr__(self) -> str:
        return f"<StrategyExecution id={self.id!s} strategy={self.strategy_id!s} success={self.success}>"


# ---------------------------------------------------------------------------
# Policy & Learning
# ---------------------------------------------------------------------------


class Policy(Base):
    """A rule or heuristic derived from learnings."""

    __tablename__ = "policies"
    __table_args__ = (
        Index("ix_policies_is_active", "is_active"),
        Index("ix_policies_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    condition: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    source_pattern_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("learning_patterns.id", ondelete="SET NULL"), nullable=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    applied_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    source_pattern: Mapped[LearningPattern | None] = relationship(back_populates="policies")

    def __repr__(self) -> str:
        return f"<Policy id={self.id!s} name={self.name!r} active={self.is_active}>"


class LearningPattern(Base):
    """Detected pattern from multiple reflection records."""

    __tablename__ = "learning_patterns"
    __table_args__ = (
        Index("ix_learning_patterns_type", "pattern_type"),
        Index("ix_learning_patterns_resolved", "is_resolved"),
        Index("ix_learning_patterns_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    pattern_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source_sessions: Mapped[list[UUID] | None] = mapped_column(ARRAY(String), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    action_taken: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    policies: Mapped[list[Policy]] = relationship(
        back_populates="source_pattern", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<LearningPattern id={self.id!s} type={self.pattern_type!r}>"


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------


class Skill(Base):
    """A reusable capability composed of multiple steps."""

    __tablename__ = "skills"
    __table_args__ = (
        Index("ix_skills_status", "status"),
        Index("ix_skills_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    task_types: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[SkillStatus] = mapped_column(
        Enum(SkillStatus, name="skill_status", create_constraint=True),
        nullable=False,
        default=SkillStatus.DRAFT,
    )
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    executions: Mapped[list[SkillExecution]] = relationship(
        back_populates="skill", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Skill id={self.id!s} name={self.name!r}>"


class SkillExecution(Base):
    """Record of a skill being applied."""

    __tablename__ = "skill_executions"
    __table_args__ = (
        Index("ix_skill_executions_skill", "skill_id"),
        Index("ix_skill_executions_session", "session_id"),
        Index("ix_skill_executions_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    skill_id: Mapped[UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    skill: Mapped[Skill] = relationship(back_populates="executions")
    session: Mapped[Session] = relationship()

    def __repr__(self) -> str:
        return f"<SkillExecution id={self.id!s} skill={self.skill_id!s} success={self.success}>"


# ---------------------------------------------------------------------------
# Experience Replay & Memory Clusters
# ---------------------------------------------------------------------------


class ExperienceRecord(Base):
    """An execution experience for RL-style replay."""

    __tablename__ = "experience_records"
    __table_args__ = (
        Index("ix_experience_records_task_type", "task_type"),
        Index("ix_experience_records_session", "session_id"),
        Index("ix_experience_records_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_used: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    context_summary: Mapped[str] = mapped_column(Text, nullable=False)
    lessons: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    session: Mapped[Session] = relationship()
    task: Mapped[Task] = relationship()

    def __repr__(self) -> str:
        return f"<ExperienceRecord id={self.id!s} type={self.task_type!r} score={self.score:.2f}>"


class MemoryCluster(Base):
    """Group of similar consolidated memories."""

    __tablename__ = "memory_clusters"
    __table_args__ = (
        Index("ix_memory_clusters_user", "user_id"),
        Index("ix_memory_clusters_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    cluster_label: Mapped[str] = mapped_column(String(255), nullable=False)
    member_ids: Mapped[list[UUID]] = mapped_column(ARRAY(String), nullable=False)
    centroid_embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    member_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    avg_importance: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship()

    def __repr__(self) -> str:
        return f"<MemoryCluster id={self.id!s} label={self.cluster_label!r} size={self.member_count}>"


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


class PerformanceMetric(Base):
    """Recorded performance metric."""

    __tablename__ = "performance_metrics"
    __table_args__ = (
        Index("ix_performance_metrics_user_type", "user_id", "metric_type"),
        Index("ix_performance_metrics_recorded_at", "recorded_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    metric_type: Mapped[MetricType] = mapped_column(
        Enum(MetricType, name="metric_type", create_constraint=True),
        nullable=False,
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped[User] = relationship()
    session: Mapped[Session | None] = relationship()

    def __repr__(self) -> str:
        return f"<PerformanceMetric id={self.id!s} type={self.metric_type.value!r} val={self.value}>"


# ---------------------------------------------------------------------------
# Phase 6: Autonomous Research Models
# ---------------------------------------------------------------------------


class KnowledgeGap(Base):
    """Identified missing knowledge or weak domain in the system."""

    __tablename__ = "knowledge_gaps"
    __table_args__ = (
        Index("ix_knowledge_gaps_domain", "domain"),
        Index("ix_knowledge_gaps_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.5")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.5")
    source_context: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class GeneratedGoal(Base):
    """An autonomously generated goal from curiosity or a knowledge gap."""

    __tablename__ = "generated_goals"
    __table_args__ = (
        Index("ix_generated_goals_status", "status"),
        Index("ix_generated_goals_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    gap_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("knowledge_gaps.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[GoalStatus] = mapped_column(
        Enum(GoalStatus, name="goal_status", create_constraint=True),
        nullable=False,
        server_default="generated",
    )
    curiosity_score: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    gap: Mapped[KnowledgeGap | None] = relationship()


class GoalTree(Base):
    """Hierarchical goal structure for long-horizon planning."""

    __tablename__ = "goal_trees"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    goal_id: Mapped[UUID] = mapped_column(
        ForeignKey("generated_goals.id", ondelete="CASCADE"), nullable=False
    )
    structure: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    goal: Mapped[GeneratedGoal] = relationship()


class SubGoal(Base):
    """A specific sub-goal derived from a GoalTree."""

    __tablename__ = "sub_goals"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    tree_id: Mapped[UUID] = mapped_column(
        ForeignKey("goal_trees.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    dependencies: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    status: Mapped[GoalStatus] = mapped_column(
        Enum(GoalStatus, name="goal_status", create_constraint=False),
        nullable=False,
        server_default="generated",
    )


class ResearchTrack(Base):
    """A dedicated research track tracking an ongoing autonomous investigation."""

    __tablename__ = "research_tracks"
    __table_args__ = (
        Index("ix_research_tracks_status", "status"),
        Index("ix_research_tracks_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    goal_id: Mapped[UUID] = mapped_column(
        ForeignKey("generated_goals.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ResearchTrackStatus] = mapped_column(
        Enum(ResearchTrackStatus, name="research_track_status", create_constraint=True),
        nullable=False,
        server_default="proposed",
    )
    progress_percentage: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    goal: Mapped[GeneratedGoal] = relationship()


class ResearchMilestone(Base):
    """A measurable milestone within a ResearchTrack."""

    __tablename__ = "research_milestones"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    track_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_tracks.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CuriosityScore(Base):
    """Curiosity evaluation metrics for a specific domain or goal."""

    __tablename__ = "curiosity_scores"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    target_id: Mapped[str] = mapped_column(String(255), nullable=False)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    novelty: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    uncertainty: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    impact: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    importance: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    total_score: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ResearchPortfolio(Base):
    """High-level management grouping for multiple research tracks."""

    __tablename__ = "research_portfolios"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[PortfolioStatus] = mapped_column(
        Enum(PortfolioStatus, name="portfolio_status", create_constraint=True),
        nullable=False,
        server_default="active",
    )
    overall_progress: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class KnowledgeGraphNode(Base):
    """SQLAlchemy backup model for Knowledge Graph Nodes (Neo4j is primary)."""

    __tablename__ = "kg_nodes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    properties: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class KnowledgeGraphEdge(Base):
    """SQLAlchemy backup model for Knowledge Graph Edges (Neo4j is primary)."""

    __tablename__ = "kg_edges"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    source_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("kg_nodes.id", ondelete="CASCADE"), nullable=False
    )
    target_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("kg_nodes.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String(255), nullable=False)
    properties: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# Phase 7: Self-Improving Research Intelligence
# ---------------------------------------------------------------------------


class ResearchReflection(Base):
    """Detailed post-execution analysis of a completed research track."""

    __tablename__ = "research_reflections"
    __table_args__ = (
        Index("ix_research_reflections_goal", "goal_id"),
        Index("ix_research_reflections_track", "track_id"),
        Index("ix_research_reflections_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    goal_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("generated_goals.id", ondelete="SET NULL"), nullable=True
    )
    track_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("research_tracks.id", ondelete="SET NULL"), nullable=True
    )
    success_score: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    completion_percentage: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    lessons_learned: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    mistakes_found: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    improvement_suggestions: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    reflection_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    goal: Mapped[GeneratedGoal | None] = relationship()
    track: Mapped[ResearchTrack | None] = relationship()


class FailurePattern(Base):
    """A recurring failure mode detected across execution history."""

    __tablename__ = "failure_patterns"
    __table_args__ = (
        Index("ix_failure_patterns_name", "pattern_name"),
        Index("ix_failure_patterns_frequency", "frequency"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    pattern_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    severity: Mapped[FailureSeverity] = mapped_column(
        Enum(FailureSeverity, name="failure_severity", create_constraint=True),
        nullable=False, server_default="medium",
    )
    recommended_fix: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ResearchStrategy(Base):
    """Long-term memory of research execution strategies."""

    __tablename__ = "research_strategies"
    __table_args__ = (
        Index("ix_research_strategies_goal_type", "goal_type"),
        Index("ix_research_strategies_domain", "domain"),
        Index("ix_research_strategies_success_rate", "success_rate"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    goal_type: Mapped[str] = mapped_column(String(100), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    success_rate: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    average_quality: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    average_cost: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    average_duration: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    times_used: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    strategy_executions: Mapped[list[ResearchStrategyExecution]] = relationship(
        back_populates="strategy", cascade="all, delete-orphan", lazy="selectin"
    )


class ResearchStrategyExecution(Base):
    """Record of a research strategy being applied to a track."""

    __tablename__ = "research_strategy_executions"
    __table_args__ = (
        Index("ix_rs_executions_strategy", "strategy_id"),
        Index("ix_rs_executions_track", "track_id"),
        Index("ix_rs_executions_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_strategies.id", ondelete="CASCADE"), nullable=False
    )
    track_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("research_tracks.id", ondelete="SET NULL"), nullable=True
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    cost_score: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    execution_time: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    token_usage: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    execution_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    strategy: Mapped[ResearchStrategy] = relationship(back_populates="strategy_executions")


class CognitiveSkill(Base):
    """A reusable skill discovered from repeated research workflows."""

    __tablename__ = "cognitive_skills"
    __table_args__ = (
        Index("ix_cognitive_skills_type", "skill_type"),
        Index("ix_cognitive_skills_success_rate", "success_rate"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    skill_type: Mapped[str] = mapped_column(String(100), nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    success_rate: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    average_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    executions: Mapped[list[CognitiveSkillExecution]] = relationship(
        back_populates="skill", cascade="all, delete-orphan", lazy="selectin"
    )


class CognitiveSkillExecution(Base):
    """Record of a cognitive skill being applied."""

    __tablename__ = "cognitive_skill_executions"
    __table_args__ = (
        Index("ix_cs_executions_skill", "skill_id"),
        Index("ix_cs_executions_track", "track_id"),
        Index("ix_cs_executions_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    skill_id: Mapped[UUID] = mapped_column(
        ForeignKey("cognitive_skills.id", ondelete="CASCADE"), nullable=False
    )
    track_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("research_tracks.id", ondelete="SET NULL"), nullable=True
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    skill: Mapped[CognitiveSkill] = relationship(back_populates="executions")


# ---------------------------------------------------------------------------
# Phase 7.6: Benchmarks and Validation
# ---------------------------------------------------------------------------

class BenchmarkRun(Base):
    """A specific execution run of a benchmark suite."""
    __tablename__ = "benchmark_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    benchmark_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)

    metrics: Mapped[list[BenchmarkMetric]] = relationship(
        back_populates="run", cascade="all, delete-orphan", lazy="selectin"
    )

class BenchmarkMetric(Base):
    """An individual metric recorded during a benchmark run."""
    __tablename__ = "benchmark_metrics"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("benchmark_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    run: Mapped[BenchmarkRun] = relationship(back_populates="metrics")

class ValidationResult(Base):
    """Closed loop validation tracking over time."""
    __tablename__ = "validation_results"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    validation_type: Mapped[str] = mapped_column(String(255), nullable=False)
    baseline_score: Mapped[float] = mapped_column(Float, nullable=False)
    new_score: Mapped[float] = mapped_column(Float, nullable=False)
    improvement_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    is_successful: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class StrategyComparison(Base):
    """Comparison of Strategy V1 vs V2 performance."""
    __tablename__ = "strategy_comparisons"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    baseline_strategy_id: Mapped[UUID] = mapped_column(ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    new_strategy_id: Mapped[UUID] = mapped_column(ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    success_rate_delta: Mapped[float] = mapped_column(Float, nullable=False)
    quality_delta: Mapped[float] = mapped_column(Float, nullable=False)
    cost_delta: Mapped[float] = mapped_column(Float, nullable=False)
    time_delta: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class SkillValidation(Base):
    """Records the reuse and ROI of a discovered skill."""
    __tablename__ = "skill_validations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    skill_id: Mapped[UUID] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    reuse_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    performance_gain: Mapped[float] = mapped_column(Float, nullable=False)
    roi_score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class GraphEvolutionSnapshot(Base):
    """Snapshot of the knowledge graph state."""
    __tablename__ = "graph_evolution_snapshots"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    concept_count: Mapped[int] = mapped_column(Integer, nullable=False)
    relationship_count: Mapped[int] = mapped_column(Integer, nullable=False)
    domain_density: Mapped[float] = mapped_column(Float, nullable=False)
    contradictions_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contradictions_resolved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class SystemHealthSnapshot(Base):
    """Tracks continuous operation stability metrics."""
    __tablename__ = "system_health_snapshots"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    memory_usage_mb: Mapped[float] = mapped_column(Float, nullable=False)
    cpu_usage_percent: Mapped[float] = mapped_column(Float, nullable=False)
    active_workers: Mapped[int] = mapped_column(Integer, nullable=False)
    uptime_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# ---------------------------------------------------------------------------
# Phase 8: Autonomous Tool Creation & Capabilities
# ---------------------------------------------------------------------------

class CapabilityGap(Base):
    """A detected gap in the agent's capabilities."""
    __tablename__ = "capability_gaps"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[Priority] = mapped_column(Enum(Priority, name="gap_priority", create_constraint=True), nullable=False, default=Priority.NORMAL)
    impact: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    estimated_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="detected")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Tool(Base):
    """A registered capability tool built by the agent."""
    __tablename__ = "tools"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(100), nullable=False, default="system")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    versions: Mapped[list[ToolVersion]] = relationship(back_populates="tool", cascade="all, delete-orphan", lazy="selectin")

class ToolVersion(Base):
    """A specific version of a tool's codebase."""
    __tablename__ = "tool_versions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    tool_id: Mapped[UUID] = mapped_column(ForeignKey("tools.id", ondelete="CASCADE"), nullable=False, index=True)
    version_string: Mapped[str] = mapped_column(String(50), nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    dependencies: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="testing")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tool: Mapped[Tool] = relationship(back_populates="versions")

class ToolExecution(Base):
    """Records an invocation of a tool version."""
    __tablename__ = "tool_executions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    tool_version_id: Mapped[UUID] = mapped_column(ForeignKey("tool_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[UUID | None] = mapped_column(ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ToolBenchmark(Base):
    """Benchmarks evaluating a specific tool version."""
    __tablename__ = "tool_benchmarks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    tool_version_id: Mapped[UUID] = mapped_column(ForeignKey("tool_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    memory_mb: Mapped[float] = mapped_column(Float, nullable=False)
    cpu_percent: Mapped[float] = mapped_column(Float, nullable=False)
    success_rate: Mapped[float] = mapped_column(Float, nullable=False)
    error_rate: Mapped[float] = mapped_column(Float, nullable=False)
    output_quality: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# ---------------------------------------------------------------------------
# Phase 9: World Model, Causal Reasoning & Scientific Discovery
# ---------------------------------------------------------------------------

class WorldModel(Base):
    """The overarching root node for a world model snapshot."""
    __tablename__ = "world_models"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class CausalRelationship(Base):
    """A discovered causal link between two concepts or entities."""
    __tablename__ = "causal_relationships"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    world_model_id: Mapped[UUID] = mapped_column(ForeignKey("world_models.id", ondelete="CASCADE"), nullable=False, index=True)
    source_concept: Mapped[str] = mapped_column(String(255), nullable=False)
    target_concept: Mapped[str] = mapped_column(String(255), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. CAUSES, INHIBITS, ENABLES
    causal_strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.1)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class Hypothesis(Base):
    """A generated testable hypothesis based on patterns or causal links."""
    __tablename__ = "hypotheses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    world_model_id: Mapped[UUID] = mapped_column(ForeignKey("world_models.id", ondelete="CASCADE"), nullable=False, index=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="proposed") # proposed, testing, validated, rejected
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Experiment(Base):
    """The design of an experiment to test a hypothesis."""
    __tablename__ = "experiments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    hypothesis_id: Mapped[UUID] = mapped_column(ForeignKey("hypotheses.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    control_group_def: Mapped[str] = mapped_column(Text, nullable=False)
    treatment_group_def: Mapped[str] = mapped_column(Text, nullable=False)
    success_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ExperimentRun(Base):
    """An actual execution of an experiment."""
    __tablename__ = "experiment_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    experiment_id: Mapped[UUID] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")
    control_results: Mapped[str | None] = mapped_column(Text, nullable=True)
    treatment_results: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    p_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Evidence(Base):
    """Data points that support or contradict a hypothesis or causal relationship."""
    __tablename__ = "evidence"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    hypothesis_id: Mapped[UUID | None] = mapped_column(ForeignKey("hypotheses.id", ondelete="CASCADE"), nullable=True)
    causal_relationship_id: Mapped[UUID | None] = mapped_column(ForeignKey("causal_relationships.id", ondelete="CASCADE"), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    supports: Mapped[bool] = mapped_column(Boolean, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class BeliefState(Base):
    """Bayesian belief state maintaining probabilities of concepts/strategies over time."""
    __tablename__ = "belief_states"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    world_model_id: Mapped[UUID] = mapped_column(ForeignKey("world_models.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_name: Mapped[str] = mapped_column(String(255), nullable=False)
    prior_probability: Mapped[float] = mapped_column(Float, nullable=False)
    posterior_probability: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class Prediction(Base):
    """A prediction made by the world model."""
    __tablename__ = "predictions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    world_model_id: Mapped[UUID] = mapped_column(ForeignKey("world_models.id", ondelete="CASCADE"), nullable=False, index=True)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    predicted_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending") # pending, verified, refuted
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class PredictionResult(Base):
    """The actual outcome compared against a prediction."""
    __tablename__ = "prediction_results"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    prediction_id: Mapped[UUID] = mapped_column(ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False, index=True)
    actual_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    is_accurate: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# ---------------------------------------------------------------------------
# Phase 10A-10F: Architecture Analysis & Benchmarking Framework
# ---------------------------------------------------------------------------

class ArchitectureVersion(Base):
    """Tracks a specific version of the system architecture."""
    __tablename__ = "architecture_versions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    parent_version_id: Mapped[UUID | None] = mapped_column(ForeignKey("architecture_versions.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="candidate") # candidate, active, superseded, rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class ArchitectureSnapshot(Base):
    """A point-in-time snapshot of the architecture's component counts and topology."""
    __tablename__ = "architecture_snapshots"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    version_id: Mapped[UUID] = mapped_column(ForeignKey("architecture_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False) # Full serialized topology
    agents_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    workers_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tools_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skills_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nodes_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    api_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ArchitectureComponent(Base):
    """An individual discovered component (agent, tool, node) within a snapshot."""
    __tablename__ = "architecture_components"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    snapshot_id: Mapped[UUID] = mapped_column(ForeignKey("architecture_snapshots.id", ondelete="CASCADE"), nullable=False, index=True)
    component_name: Mapped[str] = mapped_column(String(255), nullable=False)
    component_type: Mapped[str] = mapped_column(String(50), nullable=False) # agent, tool, worker, api, db, node
    dependencies: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    metadata_: Mapped[str | None] = mapped_column(Text, nullable=True) # JSON config
    performance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ArchitectureBenchmark(Base):
    """A benchmark execution assessing an entire architecture version."""
    __tablename__ = "architecture_benchmarks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    version_id: Mapped[UUID] = mapped_column(ForeignKey("architecture_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    latency_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    resource_score: Mapped[float] = mapped_column(Float, nullable=False)
    throughput_score: Mapped[float] = mapped_column(Float, nullable=False)
    fitness_score: Mapped[float] = mapped_column(Float, nullable=False) # The master metric
    benchmark_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ArchitectureCandidate(Base):
    """An LLM-proposed architecture change or variant."""
    __tablename__ = "architecture_candidates"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    version_id: Mapped[UUID] = mapped_column(ForeignKey("architecture_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_name: Mapped[str] = mapped_column(String(255), nullable=False)
    candidate_type: Mapped[str] = mapped_column(String(50), nullable=False) # agent_variant, workflow_variant, logic_variant
    expected_improvement: Mapped[str] = mapped_column(Text, nullable=False)
    benchmark_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending") # pending, benchmarking, validated, rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# ---------------------------------------------------------------------------
# Phase 10G-10M: Autonomous Promotion, Evolution Engine & Recursive Self-Improvement
# ---------------------------------------------------------------------------

class CognitiveGenome(Base):
    """Represents a specific architectural configuration as a genetic string."""
    __tablename__ = "cognitive_genomes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    generation: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_genome_id: Mapped[UUID | None] = mapped_column(ForeignKey("cognitive_genomes.id", ondelete="SET NULL"), nullable=True)
    genome_json: Mapped[str] = mapped_column(Text, nullable=False)
    fitness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active") # active, superseded, rejected, canary
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class GenomeMutation(Base):
    """Records a specific mutation applied to a genome."""
    __tablename__ = "genome_mutations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    genome_id: Mapped[UUID] = mapped_column(ForeignKey("cognitive_genomes.id", ondelete="CASCADE"), nullable=False, index=True)
    mutation_type: Mapped[str] = mapped_column(String(50), nullable=False) # crossover, point_mutation, structural_addition
    mutation_description: Mapped[str] = mapped_column(Text, nullable=False)
    before_state: Mapped[str] = mapped_column(Text, nullable=False)
    after_state: Mapped[str] = mapped_column(Text, nullable=False)
    fitness_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class EvolutionGeneration(Base):
    """Tracks a complete generational cycle of the evolutionary engine."""
    __tablename__ = "evolution_generations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    generation_number: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    population_size: Mapped[int] = mapped_column(Integer, nullable=False)
    best_fitness: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_fitness: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ArchitecturePromotion(Base):
    """A record of when a candidate architecture officially replaces the baseline."""
    __tablename__ = "architecture_promotions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    candidate_id: Mapped[UUID] = mapped_column(ForeignKey("architecture_candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    baseline_id: Mapped[UUID] = mapped_column(ForeignKey("architecture_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    promotion_reason: Mapped[str] = mapped_column(Text, nullable=False)
    fitness_delta: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ArchitectureRollback(Base):
    """A record of when an architecture is rolled back due to regression."""
    __tablename__ = "architecture_rollbacks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    deployment_id: Mapped[UUID] = mapped_column(ForeignKey("architecture_promotions.id", ondelete="CASCADE"), nullable=False, index=True)
    rollback_reason: Mapped[str] = mapped_column(Text, nullable=False)
    failure_metrics: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class CandidateEvaluation(Base):
    """The deep metric evaluation of a candidate before promotion decision."""
    __tablename__ = "candidate_evaluations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    candidate_id: Mapped[UUID] = mapped_column(ForeignKey("architecture_candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    latency_score: Mapped[float] = mapped_column(Float, nullable=False)
    resource_score: Mapped[float] = mapped_column(Float, nullable=False)
    failure_rate: Mapped[float] = mapped_column(Float, nullable=False)
    fitness_score: Mapped[float] = mapped_column(Float, nullable=False)
    evaluation_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class FitnessHistory(Base):
    """Historical tracking of fitness metrics over long horizons (24h, 7d, 30d)."""
    __tablename__ = "fitness_histories"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    genome_id: Mapped[UUID] = mapped_column(ForeignKey("cognitive_genomes.id", ondelete="CASCADE"), nullable=False, index=True)
    fitness_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    prediction_accuracy: Mapped[float] = mapped_column(Float, nullable=False)
    goal_completion: Mapped[float] = mapped_column(Float, nullable=False)
    resource_efficiency: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# ---------------------------------------------------------------------------
# Phase 11: Capability Verification, Generalization & Intelligence Growth
# ---------------------------------------------------------------------------

class CapabilityScore(Base):
    """Tracks absolute capability metrics for a given domain/generation."""
    __tablename__ = "capability_scores"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    generation: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(100), nullable=False) # e.g., Reasoning, Coding, Research
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class CapabilityGrowth(Base):
    """Measures the delta in capability between generations."""
    __tablename__ = "capability_growth_records"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    domain: Mapped[str] = mapped_column(String(100), nullable=False)
    previous_generation: Mapped[int] = mapped_column(Integer, nullable=False)
    current_generation: Mapped[int] = mapped_column(Integer, nullable=False)
    growth_delta: Mapped[float] = mapped_column(Float, nullable=False)
    growth_rate: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class TransferLearningRecord(Base):
    """Documents occurrences where skill in Domain A improved Domain B."""
    __tablename__ = "transfer_learning_records"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    source_domain: Mapped[str] = mapped_column(String(100), nullable=False)
    target_domain: Mapped[str] = mapped_column(String(100), nullable=False)
    transfer_gain: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class DiscoveryRecord(Base):
    """Tracks entirely novel strategies, tools, or knowledge discovered."""
    __tablename__ = "discovery_records"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    discovery_type: Mapped[str] = mapped_column(String(100), nullable=False) # Tool, Strategy, Fact, Workflow
    novelty_score: Mapped[float] = mapped_column(Float, nullable=False)
    impact_score: Mapped[float] = mapped_column(Float, nullable=False)
    reuse_score: Mapped[float] = mapped_column(Float, nullable=False)
    discovery_score: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class PeerReview(Base):
    """Peer review evaluation records verifying discoveries and hypotheses."""
    __tablename__ = "peer_reviews"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    discovery_id: Mapped[UUID | None] = mapped_column(ForeignKey("discovery_records.id", ondelete="CASCADE"), nullable=True)
    hypothesis_id: Mapped[UUID | None] = mapped_column(ForeignKey("hypotheses.id", ondelete="CASCADE"), nullable=True)
    evidence_strength: Mapped[float] = mapped_column(Float, nullable=False)
    replicability: Mapped[float] = mapped_column(Float, nullable=False)
    novelty: Mapped[float] = mapped_column(Float, nullable=False)
    consistency: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False) # accepted, rejected, disputed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class CapabilityRegression(Base):
    """Triggers and logs when evolutionary steps reduce capability."""
    __tablename__ = "capability_regressions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    domain: Mapped[str] = mapped_column(String(100), nullable=False)
    generation: Mapped[int] = mapped_column(Integer, nullable=False)
    regression_amount: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    rollback_triggered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# ---------------------------------------------------------------------------
# Phase 12: Real-World Autonomy, Long-Horizon Project Execution
# ---------------------------------------------------------------------------

class Project(Base):
    """A master container for a complex, multi-step real-world objective."""
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="planned") # planned, active, paused, failed, completed
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class ProjectMilestone(Base):
    """Major checkpoints within a Project."""
    __tablename__ = "project_milestones"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ProjectTask(Base):
    """Discrete executable steps tied to a Milestone."""
    __tablename__ = "project_tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    milestone_id: Mapped[UUID] = mapped_column(ForeignKey("project_milestones.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    estimated_effort: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    actual_effort: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class TaskExecution(Base):
    """Records an attempt to execute a specific task."""
    __tablename__ = "task_executions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    task_id: Mapped[UUID] = mapped_column(ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id: Mapped[UUID | None] = mapped_column(ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False) # running, success, failure
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_log: Mapped[str | None] = mapped_column(Text, nullable=True)

class TaskDependency(Base):
    """Directed edges representing dependencies between Tasks."""
    __tablename__ = "task_dependencies"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    task_id: Mapped[UUID] = mapped_column(ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    depends_on_task_id: Mapped[UUID] = mapped_column(ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ExecutionCheckpoint(Base):
    """State snapshots for resuming interrupted long-horizon workflows."""
    __tablename__ = "execution_checkpoints"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    state_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ResourceBudget(Base):
    """A project's allocated limits for execution."""
    __tablename__ = "resource_budgets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    max_api_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    max_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ResourceConsumption(Base):
    """Tracking actual burn rates against the ResourceBudget."""
    __tablename__ = "resource_consumptions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    api_calls_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_used_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class FailureIncident(Base):
    """An execution error detected by the FailureDetector."""
    __tablename__ = "failure_incidents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    task_id: Mapped[UUID | None] = mapped_column(ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=True, index=True)
    error_type: Mapped[str] = mapped_column(String(100), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open") # open, recovering, resolved, escalated
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class RecoveryAction(Base):
    """An action taken by the RecoveryEngine to fix a FailureIncident."""
    __tablename__ = "recovery_actions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    incident_id: Mapped[UUID] = mapped_column(ForeignKey("failure_incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False) # retry, alternative_tool, alternative_strategy, rollback
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    execution_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ExternalOutcome(Base):
    """The measurable external impact generated by a Project."""
    __tablename__ = "external_outcomes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    outcome_type: Mapped[str] = mapped_column(String(100), nullable=False) # Software Delivered, Research Published, Bug Fixed
    description: Mapped[str] = mapped_column(Text, nullable=False)
    impact_score: Mapped[float] = mapped_column(Float, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending") # pending, verified, rejected


# ---------------------------------------------------------------------------
# Phase 7: Multi-Modal Context Models
# ---------------------------------------------------------------------------


class Screenshot(Base):
    """Captured screenshot for visual analysis (Phase 7)."""
    __tablename__ = "screenshots"
    __table_args__ = (
        Index("ix_screenshots_session", "session_id"),
        Index("ix_screenshots_task", "task_id"),
        Index("ix_screenshots_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    session_id: Mapped[UUID | None] = mapped_column(ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    task_id: Mapped[UUID | None] = mapped_column(ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=True)
    image_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=True)
    viewport_width: Mapped[int] = mapped_column(Integer, nullable=False, default=1920)
    viewport_height: Mapped[int] = mapped_column(Integer, nullable=False, default=1080)
    analysis_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending") # pending, processing, complete, failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    session: Mapped[Session | None] = relationship(foreign_keys=[session_id])
    task: Mapped[Task | None] = relationship(foreign_keys=[task_id])
    visual_elements: Mapped[list[VisualElement]] = relationship(back_populates="screenshot", cascade="all, delete-orphan")
    interaction_logs: Mapped[list[InteractionLog]] = relationship(back_populates="screenshot", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Screenshot id={self.id!s} url={self.url!r} status={self.analysis_status!r}>"


class VisualElement(Base):
    """Detected visual element in a screenshot (Phase 7)."""
    __tablename__ = "visual_elements"
    __table_args__ = (
        Index("ix_visual_elements_screenshot", "screenshot_id"),
        Index("ix_visual_elements_type", "element_type"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    screenshot_id: Mapped[UUID] = mapped_column(ForeignKey("screenshots.id", ondelete="CASCADE"), nullable=False, index=True)
    element_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True) # button, input, link, text, etc.
    bbox_x1: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_y1: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_x2: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_y2: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    attributes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    screenshot: Mapped[Screenshot] = relationship(back_populates="visual_elements")

    def __repr__(self) -> str:
        return f"<VisualElement id={self.id!s} type={self.element_type!r} confidence={self.confidence}>"


class InteractionLog(Base):
    """Log of visual interaction actions (Phase 7)."""
    __tablename__ = "interaction_logs"
    __table_args__ = (
        Index("ix_interaction_logs_screenshot", "screenshot_id"),
        Index("ix_interaction_logs_session", "session_id"),
        Index("ix_interaction_logs_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    screenshot_id: Mapped[UUID | None] = mapped_column(ForeignKey("screenshots.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id: Mapped[UUID | None] = mapped_column(ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    task_id: Mapped[UUID | None] = mapped_column(ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False) # click, type, scroll, navigate
    element_id: Mapped[UUID | None] = mapped_column(ForeignKey("visual_elements.id", ondelete="SET NULL"), nullable=True)
    coordinates_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    coordinates_y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    screenshot: Mapped[Screenshot | None] = relationship(back_populates="interaction_logs")
    element: Mapped[VisualElement | None] = relationship(foreign_keys=[element_id])

    def __repr__(self) -> str:
        return f"<InteractionLog id={self.id!s} action={self.action_type!r} success={self.success}>"


# ---------------------------------------------------------------------------
# Phase 8: Swarm Orchestration Models
# ---------------------------------------------------------------------------


class DirectorAgent(Base):
    """Director agent that manages sub-orchestrators (Phase 8)."""
    __tablename__ = "director_agents"
    __table_args__ = (
        Index("ix_director_agents_status", "status"),
        Index("ix_director_agents_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="idle") # idle, active, scaling, shutdown
    max_sub_orchestrators: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    current_sub_orchestrators: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_goals_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_goals_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    swarm_goals: Mapped[list[SwarmGoal]] = relationship(back_populates="director", cascade="all, delete-orphan")
    sub_orchestrators: Mapped[list[SubOrchestrator]] = relationship(back_populates="director", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<DirectorAgent id={self.id!s} status={self.status!r} sub_orchs={self.current_sub_orchestrators}>"


class SwarmGoal(Base):
    """High-level goal for the swarm to execute (Phase 8)."""
    __tablename__ = "swarm_goals"
    __table_args__ = (
        Index("ix_swarm_goals_director", "director_id"),
        Index("ix_swarm_goals_status", "status"),
        Index("ix_swarm_goals_priority", "priority"),
        Index("ix_swarm_goals_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    director_id: Mapped[UUID] = mapped_column(ForeignKey("director_agents.id", ondelete="CASCADE"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    estimated_complexity: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    required_capabilities: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    resource_requirements: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending") # pending, planning, executing, completed, failed
    sub_task_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_sub_tasks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    director: Mapped[DirectorAgent] = relationship(back_populates="swarm_goals")
    sub_tasks: Mapped[list[SwarmSubTask]] = relationship(back_populates="goal", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<SwarmGoal id={self.id!s} status={self.status!r} priority={self.priority}>"


class SubOrchestrator(Base):
    """Sub-orchestrator that executes sub-tasks (Phase 8)."""
    __tablename__ = "sub_orchestrators"
    __table_args__ = (
        Index("ix_sub_orchestrators_director", "director_id"),
        Index("ix_sub_orchestrators_status", "status"),
        Index("ix_sub_orchestrators_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    director_id: Mapped[UUID] = mapped_column(ForeignKey("director_agents.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="idle") # idle, assigned, executing, completed, failed
    current_task_id: Mapped[UUID | None] = mapped_column(ForeignKey("swarm_sub_tasks.id", ondelete="SET NULL"), nullable=True)
    capabilities: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    current_load: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    total_tasks_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_task_duration: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    success_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    director: Mapped[DirectorAgent] = relationship(back_populates="sub_orchestrators")
    current_task: Mapped[SwarmSubTask | None] = relationship(foreign_keys=[current_task_id])
    assigned_tasks: Mapped[list[SwarmSubTask]] = relationship(back_populates="assigned_orchestrator", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<SubOrchestrator id={self.id!s} status={self.status!r} load={self.current_load}>"


class SwarmSubTask(Base):
    """Sub-task assigned to a sub-orchestrator (Phase 8)."""
    __tablename__ = "swarm_sub_tasks"
    __table_args__ = (
        Index("ix_swarm_sub_tasks_goal", "goal_id"),
        Index("ix_swarm_sub_tasks_orchestrator", "assigned_orchestrator_id"),
        Index("ix_swarm_sub_tasks_status", "status"),
        Index("ix_swarm_sub_tasks_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    goal_id: Mapped[UUID] = mapped_column(ForeignKey("swarm_goals.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_orchestrator_id: Mapped[UUID | None] = mapped_column(ForeignKey("sub_orchestrators.id", ondelete="SET NULL"), nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    dependencies: Mapped[list[UUID] | None] = mapped_column(ARRAY(String), nullable=True)
    estimated_duration: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    actual_duration: Mapped[int] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending") # pending, assigned, executing, completed, failed
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    goal: Mapped[SwarmGoal] = relationship(back_populates="sub_tasks")
    assigned_orchestrator: Mapped[SubOrchestrator | None] = relationship(back_populates="assigned_tasks", foreign_keys=[assigned_orchestrator_id])

    def __repr__(self) -> str:
        return f"<SwarmSubTask id={self.id!s} status={self.status!r} progress={self.progress}>"


# ---------------------------------------------------------------------------
# Phase 13: Cognitive Operating System Models
# ---------------------------------------------------------------------------


class CognitiveTask(Base):
    """A cognitive task managed by the cognitive kernel."""

    __tablename__ = "cognitive_tasks"
    __table_args__ = (
        Index("ix_cognitive_tasks_status", "status"),
        Index("ix_cognitive_tasks_priority", "priority"),
        Index("ix_cognitive_tasks_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    priority: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    requires_attention: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attention_allocated: Mapped[float] = mapped_column(Float, nullable=True)
    cognitive_resources: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<CognitiveTask id={self.id!s} type={self.task_type!r} status={self.status!r}>"


class AttentionRecord(Base):
    """Record of attention allocation and usage."""

    __tablename__ = "attention_records"
    __table_args__ = (
        Index("ix_attention_records_task", "task_id"),
        Index("ix_attention_records_level", "attention_level"),
        Index("ix_attention_records_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    task_id: Mapped[UUID | None] = mapped_column(String(255), nullable=True)
    attention_level: Mapped[AttentionLevel] = mapped_column(
        Enum(AttentionLevel, name="attention_level", create_constraint=True),
        nullable=False,
    )
    allocated_amount: Mapped[float] = mapped_column(Float, nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)
    processing_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    cognitive_resources: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<AttentionRecord id={self.id!s} level={self.attention_level.value!r}>"


class MemoryLink(Base):
    """Links between memories in the unified memory graph."""

    __tablename__ = "memory_links"
    __table_args__ = (
        Index("ix_memory_links_source", "source_memory_id"),
        Index("ix_memory_links_target", "target_memory_id"),
        Index("ix_memory_links_type", "link_type"),
        Index("ix_memory_links_strength", "strength"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    source_memory_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    target_memory_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    link_type: Mapped[str] = mapped_column(String(50), nullable=False)
    strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<MemoryLink id={self.id!s} type={self.link_type!r} strength={self.strength:.2f}>"


class ResearchProgram(Base):
    """A long-running autonomous research program."""

    __tablename__ = "research_programs"
    __table_args__ = (
        Index("ix_research_programs_status", "status"),
        Index("ix_research_programs_domain", "domain"),
        Index("ix_research_programs_created_at", "created_at"),
        {"extend_existing": True}
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[ProgramStatus] = mapped_column(
        Enum(ProgramStatus, name="program_status", create_constraint=True),
        nullable=False,
        default=ProgramStatus.DRAFT,
    )
    hypotheses: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    experiments: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    insights: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<ResearchProgram id={self.id!s} title={self.title!r} status={self.status.value!r}>"


class AgentIdentity(Base):
    """Identity information for an agent in the society."""

    __tablename__ = "agent_identities"
    __table_args__ = (
        Index("ix_agent_identities_agent_id", "agent_id"),
        Index("ix_agent_identities_status", "status"),
        Index("ix_agent_identities_type", "agent_type"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus, name="agent_status", create_constraint=True),
        nullable=False,
        default=AgentStatus.IDLE,
    )
    capabilities: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    reputation: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    core_values: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    personality_traits: Mapped[dict[str, float] | None] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_active: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AgentIdentity id={self.id!s} agent_id={self.agent_id!r} status={self.status.value!r}>"


class MissionState(Base):
    """A long-term mission for the identity system."""

    __tablename__ = "mission_states"
    __table_args__ = (
        Index("ix_mission_states_status", "status"),
        Index("ix_mission_states_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[MissionStatus] = mapped_column(
        Enum(MissionStatus, name="mission_status", create_constraint=True),
        nullable=False,
        default=MissionStatus.DRAFT,
    )
    goals: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    results: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<MissionState id={self.id!s} title={self.title!r} status={self.status.value!r}>"


class CognitiveMetric(Base):
    """Cognitive performance metrics for the system."""

    __tablename__ = "cognitive_metrics"
    __table_args__ = (
        Index("ix_cognitive_metrics_type", "metric_type"),
        Index("ix_cognitive_metrics_timestamp", "timestamp"),
        {"extend_existing": True}
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    metric_type: Mapped[CognitiveMetricType] = mapped_column(
        Enum(CognitiveMetricType, name="cognitive_metric_type", create_constraint=True),
        nullable=False,
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<CognitiveMetric id={self.id!s} type={self.metric_type.value!r} value={self.value:.2f}>"


# ---------------------------------------------------------------------------
# Phase 17: Runtime Completion & Production Readiness
# ---------------------------------------------------------------------------


class Objective(Base):
    """A durable unit of autonomous intent with persistence."""

    __tablename__ = "objectives"
    __table_args__ = (
        Index("ix_objectives_status", "status"),
        Index("ix_objectives_priority", "priority"),
        Index("ix_objectives_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    objective_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    status: Mapped[ObjectiveStatus] = mapped_column(
        Enum(ObjectiveStatus, name="objective_status", create_constraint=True),
        nullable=False,
        default=ObjectiveStatus.ACTIVE,
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    progress_records: Mapped[list["ObjectiveProgress"]] = relationship(
        back_populates="objective", cascade="all, delete-orphan", lazy="selectin"
    )
    checkpoints: Mapped[list["ObjectiveCheckpoint"]] = relationship(
        back_populates="objective", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Objective id={self.id!s} objective_id={self.objective_id!r} status={self.status.value!r}>"


class ObjectiveProgress(Base):
    """Progress tracking for autonomous objectives."""

    __tablename__ = "objective_progress"
    __table_args__ = (
        Index("ix_objective_progress_objective", "objective_id"),
        Index("ix_objective_progress_status", "status"),
        Index("ix_objective_progress_timestamp", "timestamp"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    objective_id: Mapped[UUID] = mapped_column(
        ForeignKey("objectives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    objective: Mapped[Objective] = relationship(back_populates="progress_records")

    def __repr__(self) -> str:
        return f"<ObjectiveProgress id={self.id!s} objective={self.objective_id!s} status={self.status!r}>"


class ObjectiveCheckpoint(Base):
    """Checkpoint for objective state restoration."""

    __tablename__ = "objective_checkpoints"
    __table_args__ = (
        Index("ix_objective_checkpoints_objective", "objective_id"),
        Index("ix_objective_checkpoints_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)
    objective_id: Mapped[UUID] = mapped_column(
        ForeignKey("objectives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    checkpoint_name: Mapped[str] = mapped_column(String(255), nullable=False)
    state_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    progress_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    objective: Mapped[Objective] = relationship(back_populates="checkpoints")

    def __repr__(self) -> str:
        return f"<ObjectiveCheckpoint id={self.id!s} objective={self.objective_id!s} name={self.checkpoint_name!r}>"
