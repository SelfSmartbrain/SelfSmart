"""Phase 6 autonomous research models.

Revision ID: 003
Revises: 002
Create Date: 2026-06-13 11:15:00.000000+00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


research_track_status_enum = postgresql.ENUM(
    "proposed", "active", "paused", "completed", "terminated",
    name="research_track_status",
    create_type=False,
)

portfolio_status_enum = postgresql.ENUM(
    "active", "archived",
    name="portfolio_status",
    create_type=False,
)

goal_status_enum = postgresql.ENUM(
    "generated", "approved", "rejected", "in_progress", "achieved", "failed",
    name="goal_status",
    create_type=False,
)


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE research_track_status AS ENUM ('proposed', 'active', 'paused', 'completed', 'terminated')")
    op.execute("CREATE TYPE portfolio_status AS ENUM ('active', 'archived')")
    op.execute("CREATE TYPE goal_status AS ENUM ('generated', 'approved', 'rejected', 'in_progress', 'achieved', 'failed')")

    # ---- knowledge_gaps ----
    op.create_table(
        "knowledge_gaps",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("importance", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("source_context", postgresql.JSONB(), nullable=True),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_knowledge_gaps_domain", "knowledge_gaps", ["domain"])
    op.create_index("ix_knowledge_gaps_created_at", "knowledge_gaps", ["created_at"])

    # ---- generated_goals ----
    op.create_table(
        "generated_goals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("gap_id", sa.Uuid(), sa.ForeignKey("knowledge_gaps.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", goal_status_enum, nullable=False, server_default="generated"),
        sa.Column("curiosity_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_generated_goals_status", "generated_goals", ["status"])
    op.create_index("ix_generated_goals_created_at", "generated_goals", ["created_at"])

    # ---- goal_trees ----
    op.create_table(
        "goal_trees",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("goal_id", sa.Uuid(), sa.ForeignKey("generated_goals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("structure", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ---- sub_goals ----
    op.create_table(
        "sub_goals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tree_id", sa.Uuid(), sa.ForeignKey("goal_trees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("dependencies", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("status", goal_status_enum, nullable=False, server_default="generated"),
    )

    # ---- research_tracks ----
    op.create_table(
        "research_tracks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("goal_id", sa.Uuid(), sa.ForeignKey("generated_goals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", research_track_status_enum, nullable=False, server_default="proposed"),
        sa.Column("progress_percentage", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_research_tracks_status", "research_tracks", ["status"])
    op.create_index("ix_research_tracks_created_at", "research_tracks", ["created_at"])

    # ---- research_milestones ----
    op.create_table(
        "research_milestones",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("track_id", sa.Uuid(), sa.ForeignKey("research_tracks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("evidence", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ---- curiosity_scores ----
    op.create_table(
        "curiosity_scores",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("target_id", sa.String(255), nullable=False),
        sa.Column("target_type", sa.String(100), nullable=False),
        sa.Column("novelty", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("uncertainty", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("impact", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("importance", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ---- research_portfolios ----
    op.create_table(
        "research_portfolios",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", portfolio_status_enum, nullable=False, server_default="active"),
        sa.Column("overall_progress", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ---- kg_nodes ----
    op.create_table(
        "kg_nodes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("properties", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ---- kg_edges ----
    op.create_table(
        "kg_edges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_node_id", sa.Uuid(), sa.ForeignKey("kg_nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_node_id", sa.Uuid(), sa.ForeignKey("kg_nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_type", sa.String(255), nullable=False),
        sa.Column("properties", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("kg_edges")
    op.drop_table("kg_nodes")
    op.drop_table("research_portfolios")
    op.drop_table("curiosity_scores")
    op.drop_table("research_milestones")
    op.drop_table("research_tracks")
    op.drop_table("sub_goals")
    op.drop_table("goal_trees")
    op.drop_table("generated_goals")
    op.drop_table("knowledge_gaps")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS goal_status")
    op.execute("DROP TYPE IF EXISTS portfolio_status")
    op.execute("DROP TYPE IF EXISTS research_track_status")
