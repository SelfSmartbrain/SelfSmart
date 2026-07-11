"""Phase 5 meta learning models.

Revision ID: 002
Revises: 001
Create Date: 2026-06-13 10:50:00.000000+00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


task_type_enum = postgresql.ENUM(
    "research", "coding", "planning", "writing", "analysis", "automation", "data_processing", "multi_step_reasoning",
    name="task_type",
    create_type=False,
)

strategy_status_enum = postgresql.ENUM(
    "active", "deprecated", "testing",
    name="strategy_status",
    create_type=False,
)

metric_type_enum = postgresql.ENUM(
    "success_rate", "token_usage", "execution_latency", "memory_hit_rate", "strategy_effectiveness", "reflection_quality", "tool_utilization",
    name="metric_type",
    create_type=False,
)

skill_status_enum = postgresql.ENUM(
    "active", "draft", "deprecated",
    name="skill_status",
    create_type=False,
)


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE task_type AS ENUM ('research', 'coding', 'planning', 'writing', 'analysis', 'automation', 'data_processing', 'multi_step_reasoning')")
    op.execute("CREATE TYPE strategy_status AS ENUM ('active', 'deprecated', 'testing')")
    op.execute("CREATE TYPE metric_type AS ENUM ('success_rate', 'token_usage', 'execution_latency', 'memory_hit_rate', 'strategy_effectiveness', 'reflection_quality', 'tool_utilization')")
    op.execute("CREATE TYPE skill_status AS ENUM ('active', 'draft', 'deprecated')")

    # ---- strategies ----
    op.create_table(
        "strategies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("task_type", task_type_enum, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("steps", postgresql.JSONB(), nullable=False),
        sa.Column("source_session_id", sa.Uuid(), sa.ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("success_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_duration_ms", sa.Integer(), nullable=True),
        sa.Column("avg_tokens", sa.Integer(), nullable=True),
        sa.Column("status", strategy_status_enum, nullable=False, server_default="testing"),
        sa.Column("is_global", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("embedding_id", sa.String(255), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_strategies_task_type", "strategies", ["task_type"])
    op.create_index("ix_strategies_status", "strategies", ["status"])
    op.create_index("ix_strategies_is_global", "strategies", ["is_global"])
    op.create_index("ix_strategies_created_at", "strategies", ["created_at"])

    # ---- strategy_executions ----
    op.create_table(
        "strategy_executions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("strategy_id", sa.Uuid(), sa.ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.Uuid(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_strategy_executions_strategy", "strategy_executions", ["strategy_id"])
    op.create_index("ix_strategy_executions_session", "strategy_executions", ["session_id"])
    op.create_index("ix_strategy_executions_task", "strategy_executions", ["task_id"])
    op.create_index("ix_strategy_executions_created_at", "strategy_executions", ["created_at"])

    # ---- learning_patterns ----
    op.create_table(
        "learning_patterns",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("pattern_type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("frequency", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_sessions", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("action_taken", sa.Text(), nullable=True),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_learning_patterns_type", "learning_patterns", ["pattern_type"])
    op.create_index("ix_learning_patterns_resolved", "learning_patterns", ["is_resolved"])
    op.create_index("ix_learning_patterns_created_at", "learning_patterns", ["created_at"])

    # ---- policies ----
    op.create_table(
        "policies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("condition", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("source_pattern_id", sa.Uuid(), sa.ForeignKey("learning_patterns.id", ondelete="SET NULL"), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("applied_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_policies_is_active", "policies", ["is_active"])
    op.create_index("ix_policies_created_at", "policies", ["created_at"])

    # ---- skills ----
    op.create_table(
        "skills",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("steps", postgresql.JSONB(), nullable=False),
        sa.Column("task_types", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("avg_duration_ms", sa.Integer(), nullable=True),
        sa.Column("status", skill_status_enum, nullable=False, server_default="draft"),
        sa.Column("embedding_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_skills_status", "skills", ["status"])
    op.create_index("ix_skills_created_at", "skills", ["created_at"])

    # ---- skill_executions ----
    op.create_table(
        "skill_executions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("skill_id", sa.Uuid(), sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_skill_executions_skill", "skill_executions", ["skill_id"])
    op.create_index("ix_skill_executions_session", "skill_executions", ["session_id"])
    op.create_index("ix_skill_executions_created_at", "skill_executions", ["created_at"])

    # ---- experience_records ----
    op.create_table(
        "experience_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.Uuid(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_type", sa.String(100), nullable=False),
        sa.Column("strategy_used", postgresql.JSONB(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("context_summary", sa.Text(), nullable=False),
        sa.Column("lessons", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("embedding_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_experience_records_task_type", "experience_records", ["task_type"])
    op.create_index("ix_experience_records_session", "experience_records", ["session_id"])
    op.create_index("ix_experience_records_created_at", "experience_records", ["created_at"])

    # ---- memory_clusters ----
    op.create_table(
        "memory_clusters",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cluster_label", sa.String(255), nullable=False),
        sa.Column("member_ids", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("centroid_embedding_id", sa.String(255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("member_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("avg_importance", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_memory_clusters_user", "memory_clusters", ["user_id"])
    op.create_index("ix_memory_clusters_created_at", "memory_clusters", ["created_at"])

    # ---- performance_metrics ----
    op.create_table(
        "performance_metrics",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("metric_type", metric_type_enum, nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_performance_metrics_user_type", "performance_metrics", ["user_id", "metric_type"])
    op.create_index("ix_performance_metrics_recorded_at", "performance_metrics", ["recorded_at"])


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("performance_metrics")
    op.drop_table("memory_clusters")
    op.drop_table("experience_records")
    op.drop_table("skill_executions")
    op.drop_table("skills")
    op.drop_table("policies")
    op.drop_table("learning_patterns")
    op.drop_table("strategy_executions")
    op.drop_table("strategies")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS skill_status")
    op.execute("DROP TYPE IF EXISTS metric_type")
    op.execute("DROP TYPE IF EXISTS strategy_status")
    op.execute("DROP TYPE IF EXISTS task_type")
