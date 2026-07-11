"""Phase 7: Self-Improving Research Intelligence tables.

Revision ID: 004
Revises: 003
Create Date: 2024-01-01 00:00:00.000000
"""

from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004_phase7_cognition"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    """Create Phase 7 tables for self-improving research intelligence."""

    # 1. Create failure_severity enum
    failure_severity_enum = postgresql.ENUM(
        "low", "medium", "high", "critical",
        name="failure_severity",
        create_type=False,  # We'll create it manually
    )
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'failure_severity') THEN
                CREATE TYPE failure_severity AS ENUM ('low', 'medium', 'high', 'critical');
            END IF;
        END
        $$;
    """)

    # 2. research_reflections
    op.create_table(
        "research_reflections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("goal_id", sa.Uuid(), sa.ForeignKey("generated_goals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("track_id", sa.Uuid(), sa.ForeignKey("research_tracks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("success_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("completion_percentage", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("lessons_learned", postgresql.JSONB(), nullable=True),
        sa.Column("mistakes_found", postgresql.JSONB(), nullable=True),
        sa.Column("improvement_suggestions", postgresql.JSONB(), nullable=True),
        sa.Column("reflection_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_reflections_goal", "research_reflections", ["goal_id"])
    op.create_index("ix_research_reflections_track", "research_reflections", ["track_id"])
    op.create_index("ix_research_reflections_created_at", "research_reflections", ["created_at"])

    # 3. failure_patterns
    op.create_table(
        "failure_patterns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pattern_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("frequency", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("severity", failure_severity_enum, nullable=False, server_default=sa.text("'medium'")),
        sa.Column("recommended_fix", sa.Text(), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_failure_patterns_name", "failure_patterns", ["pattern_name"])
    op.create_index("ix_failure_patterns_frequency", "failure_patterns", ["frequency"])

    # 4. research_strategies
    op.create_table(
        "research_strategies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("goal_type", sa.String(100), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("success_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("average_quality", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("average_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("average_duration", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("times_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_strategies_goal_type", "research_strategies", ["goal_type"])
    op.create_index("ix_research_strategies_domain", "research_strategies", ["domain"])
    op.create_index("ix_research_strategies_success_rate", "research_strategies", ["success_rate"])

    # 5. research_strategy_executions
    op.create_table(
        "research_strategy_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("strategy_id", sa.Uuid(), sa.ForeignKey("research_strategies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("track_id", sa.Uuid(), sa.ForeignKey("research_tracks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("cost_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("execution_time", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("token_usage", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("execution_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rs_executions_strategy", "research_strategy_executions", ["strategy_id"])
    op.create_index("ix_rs_executions_track", "research_strategy_executions", ["track_id"])
    op.create_index("ix_rs_executions_created_at", "research_strategy_executions", ["created_at"])

    # 6. cognitive_skills
    op.create_table(
        "cognitive_skills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("skill_type", sa.String(100), nullable=False),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("average_duration", sa.Float(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cognitive_skills_type", "cognitive_skills", ["skill_type"])
    op.create_index("ix_cognitive_skills_success_rate", "cognitive_skills", ["success_rate"])

    # 7. cognitive_skill_executions
    op.create_table(
        "cognitive_skill_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.Uuid(), sa.ForeignKey("cognitive_skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("track_id", sa.Uuid(), sa.ForeignKey("research_tracks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cs_executions_skill", "cognitive_skill_executions", ["skill_id"])
    op.create_index("ix_cs_executions_track", "cognitive_skill_executions", ["track_id"])
    op.create_index("ix_cs_executions_created_at", "cognitive_skill_executions", ["created_at"])

    # 8. cognitive_metrics
    op.create_table(
        "cognitive_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("metric_name", sa.String(255), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cognitive_metrics_name", "cognitive_metrics", ["metric_name"])
    op.create_index("ix_cognitive_metrics_recorded_at", "cognitive_metrics", ["recorded_at"])


def downgrade() -> None:
    """Drop Phase 7 tables."""
    op.drop_table("cognitive_metrics")
    op.drop_table("cognitive_skill_executions")
    op.drop_table("cognitive_skills")
    op.drop_table("research_strategy_executions")
    op.drop_table("research_strategies")
    op.drop_table("failure_patterns")
    op.drop_table("research_reflections")

    # Drop enum
    op.execute("DROP TYPE IF EXISTS failure_severity")
