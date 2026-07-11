"""Phase 10G evolution tables

Revision ID: 009_phase10g_evolution
Revises: 008_phase10_architecture
Create Date: 2026-06-14 17:56:03.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '009_phase10g_evolution'
down_revision: Union[str, None] = '008_phase10_architecture'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # cognitive_genomes
    op.create_table(
        'cognitive_genomes',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('generation_id', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('parent_ids', sa.ARRAY(sa.UUID(as_uuid=True)), nullable=True),
        sa.Column('genome_data', postgresql.JSONB, nullable=False),
        sa.Column('fitness_score', sa.Float, nullable=True),
        sa.Column('is_active', sa.Boolean, server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # genome_mutations
    op.create_table(
        'genome_mutations',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('genome_id', sa.UUID(as_uuid=True), sa.ForeignKey('cognitive_genomes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mutation_type', sa.String(length=100), nullable=False),
        sa.Column('mutation_details', postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # evolution_generations
    op.create_table(
        'evolution_generations',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('generation_number', sa.Integer, nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('metrics', postgresql.JSONB, nullable=True)
    )

    # architecture_promotions
    op.create_table(
        'architecture_promotions',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('genome_id', sa.UUID(as_uuid=True), sa.ForeignKey('cognitive_genomes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('promoted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('reason', sa.Text, nullable=True),
        sa.Column('performance_metrics', postgresql.JSONB, nullable=True)
    )

    # architecture_rollbacks
    op.create_table(
        'architecture_rollbacks',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('genome_id', sa.UUID(as_uuid=True), sa.ForeignKey('cognitive_genomes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rolled_back_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('reason', sa.Text, nullable=True),
        sa.Column('failure_metrics', postgresql.JSONB, nullable=True)
    )

    # candidate_evaluations
    op.create_table(
        'candidate_evaluations',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('genome_id', sa.UUID(as_uuid=True), sa.ForeignKey('cognitive_genomes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('evaluation_task_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('score', sa.Float, nullable=False),
        sa.Column('details', postgresql.JSONB, nullable=True),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )

    # fitness_histories
    op.create_table(
        'fitness_histories',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('genome_id', sa.UUID(as_uuid=True), sa.ForeignKey('cognitive_genomes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('fitness_score', sa.Float, nullable=False),
        sa.Column('components', postgresql.JSONB, nullable=True)
    )


def downgrade() -> None:
    op.drop_table('fitness_histories')
    op.drop_table('candidate_evaluations')
    op.drop_table('architecture_rollbacks')
    op.drop_table('architecture_promotions')
    op.drop_table('evolution_generations')
    op.drop_table('genome_mutations')
    op.drop_table('cognitive_genomes')
