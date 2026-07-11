"""phase9_world_model

Revision ID: 007_phase9_world_model
Revises: 006_phase8_tools
Create Date: 2026-06-14 17:18:49.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '007_phase9_world_model'
down_revision: Union[str, None] = '006_phase8_tools'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # world_models
    op.create_table(
        'world_models',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # causal_relationships
    op.create_table(
        'causal_relationships',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('world_model_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('world_models.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_entity', sa.String(), nullable=False),
        sa.Column('target_entity', sa.String(), nullable=False),
        sa.Column('relationship_type', sa.String(), nullable=False),
        sa.Column('confidence', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # hypotheses
    op.create_table(
        'hypotheses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('world_model_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('world_models.id', ondelete='CASCADE'), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('status', sa.String(), server_default="'proposed'", nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # experiments
    op.create_table(
        'experiments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('hypothesis_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hypotheses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('setup_parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # experiment_runs
    op.create_table(
        'experiment_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('experiment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('experiments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(), server_default="'pending'", nullable=False),
        sa.Column('result_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # evidence
    op.create_table(
        'evidence',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('hypothesis_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hypotheses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('experiment_run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('experiment_runs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('supports_hypothesis', sa.Boolean(), nullable=False),
        sa.Column('weight', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # belief_states
    op.create_table(
        'belief_states',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('world_model_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('world_models.id', ondelete='CASCADE'), nullable=False),
        sa.Column('entity_name', sa.String(), nullable=False),
        sa.Column('state_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('confidence', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # predictions
    op.create_table(
        'predictions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('world_model_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('world_models.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_entity', sa.String(), nullable=False),
        sa.Column('predicted_state', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('predicted_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('confidence', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # prediction_results
    op.create_table(
        'prediction_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('prediction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('predictions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actual_state', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('actual_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accuracy_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )


def downgrade() -> None:
    op.drop_table('prediction_results')
    op.drop_table('predictions')
    op.drop_table('belief_states')
    op.drop_table('evidence')
    op.drop_table('experiment_runs')
    op.drop_table('experiments')
    op.drop_table('hypotheses')
    op.drop_table('causal_relationships')
    op.drop_table('world_models')
