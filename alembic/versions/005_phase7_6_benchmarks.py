"""Phase 7.6 Benchmark models

Revision ID: 005_phase7_6_benchmarks
Revises: 004_phase7_cognition
Create Date: 2026-06-14 17:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005_phase7_6_benchmarks'
down_revision: Union[str, None] = '004_phase7_cognition'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # benchmark_runs
    op.create_table(
        'benchmark_runs',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_benchmark_runs_status', 'benchmark_runs', ['status'])

    # benchmark_metrics
    op.create_table(
        'benchmark_metrics',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('metric_name', sa.String(), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['benchmark_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_benchmark_metrics_run_id', 'benchmark_metrics', ['run_id'])

    # validation_results
    op.create_table(
        'validation_results',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('target_type', sa.String(), nullable=False),
        sa.Column('target_id', sa.UUID(), nullable=False),
        sa.Column('is_valid', sa.Boolean(), nullable=False),
        sa.Column('errors', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_validation_results_target', 'validation_results', ['target_type', 'target_id'])

    # strategy_comparisons
    op.create_table(
        'strategy_comparisons',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('baseline_strategy_id', sa.UUID(), nullable=False),
        sa.Column('candidate_strategy_id', sa.UUID(), nullable=False),
        sa.Column('comparison_results', postgresql.JSONB(), nullable=False),
        sa.Column('winner_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # skill_validations
    op.create_table(
        'skill_validations',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('skill_id', sa.UUID(), nullable=False),
        sa.Column('validation_score', sa.Float(), nullable=False),
        sa.Column('test_cases_passed', sa.Integer(), nullable=False),
        sa.Column('test_cases_total', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_skill_validations_skill_id', 'skill_validations', ['skill_id'])

    # graph_evolution_snapshots
    op.create_table(
        'graph_evolution_snapshots',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('graph_id', sa.UUID(), nullable=False),
        sa.Column('node_count', sa.Integer(), nullable=False),
        sa.Column('edge_count', sa.Integer(), nullable=False),
        sa.Column('snapshot_data', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_graph_evolution_snapshots_graph_id', 'graph_evolution_snapshots', ['graph_id'])

    # system_health_snapshots
    op.create_table(
        'system_health_snapshots',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('cpu_usage', sa.Float(), nullable=False),
        sa.Column('memory_usage', sa.Float(), nullable=False),
        sa.Column('active_tasks', sa.Integer(), nullable=False),
        sa.Column('health_score', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('system_health_snapshots')
    op.drop_table('graph_evolution_snapshots')
    op.drop_table('skill_validations')
    op.drop_table('strategy_comparisons')
    op.drop_table('validation_results')
    op.drop_table('benchmark_metrics')
    op.drop_table('benchmark_runs')
