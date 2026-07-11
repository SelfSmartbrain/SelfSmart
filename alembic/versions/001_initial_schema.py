"""Initial schema — all tables for the Autonomous Agent Platform.

Revision ID: 001
Revises: None
Create Date: 2026-06-13 09:00:00.000000+00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Enum types
# ---------------------------------------------------------------------------

session_status_enum = postgresql.ENUM(
    "pending", "active", "completed", "failed", "cancelled",
    name="session_status",
    create_type=True,
)

task_status_enum = postgresql.ENUM(
    "pending", "in_progress", "completed", "failed", "blocked", "cancelled",
    name="task_status",
    create_type=True,
)

execution_status_enum = postgresql.ENUM(
    "running", "completed", "failed", "timeout",
    name="execution_status",
    create_type=True,
)

memory_type_enum = postgresql.ENUM(
    "episodic", "semantic", "procedural",
    name="memory_type",
    create_type=True,
)

source_type_enum = postgresql.ENUM(
    "arxiv", "web", "wikipedia", "pdf", "manual",
    name="source_type",
    create_type=True,
)

reflection_type_enum = postgresql.ENUM(
    "task", "session", "strategy",
    name="reflection_type",
    create_type=True,
)

priority_enum = postgresql.ENUM(
    "low", "normal", "high", "critical",
    name="priority",
    create_type=True,
)


def upgrade() -> None:
    """Create all tables and indexes for the platform."""
    # Create UUID extension for uuid_generate_v7()
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    
    # Enum types will be created automatically by SQLAlchemy when tables are created

    # ---- users ----
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("api_key_hash", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ---- sessions ----
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("status", session_status_enum, nullable=False, server_default="pending"),
        sa.Column("context", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_status", "sessions", ["status"])
    op.create_index("ix_sessions_user_status", "sessions", ["user_id", "status"])
    op.create_index("ix_sessions_created_at", "sessions", ["created_at"])

    # ---- tasks ----
    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_task_id", sa.Uuid(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", task_status_enum, nullable=False, server_default="pending"),
        sa.Column("priority", priority_enum, nullable=False, server_default="normal"),
        sa.Column("agent_type", sa.String(100), nullable=True),
        sa.Column("dependencies", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tasks_session_id", "tasks", ["session_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_session_status", "tasks", ["session_id", "status"])
    op.create_index("ix_tasks_status_priority", "tasks", ["status", "priority"])
    op.create_index("ix_tasks_parent", "tasks", ["parent_task_id"])
    op.create_index("ix_tasks_created_at", "tasks", ["created_at"])

    # ---- executions ----
    op.create_table(
        "executions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("task_id", sa.Uuid(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_type", sa.String(100), nullable=False),
        sa.Column("input_data", postgresql.JSONB(), nullable=True),
        sa.Column("output_data", postgresql.JSONB(), nullable=True),
        sa.Column("status", execution_status_enum, nullable=False, server_default="running"),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_executions_task_id", "executions", ["task_id"])
    op.create_index("ix_executions_status", "executions", ["status"])
    op.create_index("ix_executions_created_at", "executions", ["created_at"])

    # ---- memories ----
    op.create_table(
        "memories",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("memory_type", memory_type_enum, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("importance_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("access_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_accessed", sa.DateTime(timezone=True), nullable=True),
        sa.Column("embedding_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_memories_user_id", "memories", ["user_id"])
    op.create_index("ix_memories_memory_type", "memories", ["memory_type"])
    op.create_index("ix_memories_user_type", "memories", ["user_id", "memory_type"])
    op.create_index("ix_memories_session", "memories", ["session_id"])
    op.create_index("ix_memories_importance", "memories", ["importance_score"])
    op.create_index("ix_memories_last_accessed", "memories", ["last_accessed"])
    op.create_index("ix_memories_created_at", "memories", ["created_at"])

    # ---- knowledge_documents ----
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(1000), nullable=False),
        sa.Column("source", sa.String(2000), nullable=False),
        sa.Column("source_type", source_type_enum, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_kdocs_source_type", "knowledge_documents", ["source_type"])
    op.create_index("ix_kdocs_created_at", "knowledge_documents", ["created_at"])

    # ---- knowledge_chunks ----
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding_id", sa.String(255), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_kchunks_document", "knowledge_chunks", ["document_id"])
    op.create_index("ix_kchunks_document_index", "knowledge_chunks", ["document_id", "chunk_index"], unique=True)

    # ---- agent_logs ----
    op.create_table(
        "agent_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.Uuid(), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agent_type", sa.String(100), nullable=False),
        sa.Column("action", sa.String(200), nullable=False),
        sa.Column("input_summary", sa.Text(), nullable=True),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_logs_session", "agent_logs", ["session_id"])
    op.create_index("ix_agent_logs_task", "agent_logs", ["task_id"])
    op.create_index("ix_agent_logs_agent_type", "agent_logs", ["agent_type"])
    op.create_index("ix_agent_logs_created_at", "agent_logs", ["created_at"])

    # ---- reflection_records ----
    op.create_table(
        "reflection_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.Uuid(), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reflection_type", reflection_type_enum, nullable=False),
        sa.Column("successes", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("failures", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("root_causes", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("improvements", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("applied", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_reflections_session", "reflection_records", ["session_id"])
    op.create_index("ix_reflections_type", "reflection_records", ["reflection_type"])
    op.create_index("ix_reflections_applied", "reflection_records", ["applied"])
    op.create_index("ix_reflections_created_at", "reflection_records", ["created_at"])


def downgrade() -> None:
    """Drop all tables and enum types."""
    try:
        # Drop tables in reverse dependency order
        op.drop_table("reflection_records")
        op.drop_table("agent_logs")
        op.drop_table("knowledge_chunks")
        op.drop_table("knowledge_documents")
        op.drop_table("memories")
        op.drop_table("executions")
        op.drop_table("tasks")
        op.drop_table("sessions")
        op.drop_table("users")

        # Drop enum types
        priority_enum.drop(op)
        reflection_type_enum.drop(op)
        source_type_enum.drop(op)
        memory_type_enum.drop(op)
        execution_status_enum.drop(op)
        task_status_enum.drop(op)
        session_status_enum.drop(op)
    except Exception as e:
        raise Exception(f"Error during downgrade: {e}")
