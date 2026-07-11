"""Phase 10 Architecture

Revision ID: 008_phase10_architecture
Revises: 007_phase9_world_model
Create Date: 2026-06-14 17:25:29.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '008_phase10_architecture'
down_revision: Union[str, None] = '007_phase9_world_model'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'architecture_versions',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
    )

    op.create_table(
        'architecture_snapshots',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('version_id', sa.UUID(as_uuid=True), sa.ForeignKey('architecture_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('snapshot_hash', sa.String(), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'architecture_components',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('snapshot_id', sa.UUID(as_uuid=True), sa.ForeignKey('architecture_snapshots.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'architecture_benchmarks',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('snapshot_id', sa.UUID(as_uuid=True), sa.ForeignKey('architecture_snapshots.id', ondelete='CASCADE'), nullable=False),
        sa.Column('metric_name', sa.String(), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'architecture_candidates',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('snapshot_id', sa.UUID(as_uuid=True), sa.ForeignKey('architecture_snapshots.id', ondelete='CASCADE'), nullable=False),
        sa.Column('candidate_name', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('architecture_candidates')
    op.drop_table('architecture_benchmarks')
    op.drop_table('architecture_components')
    op.drop_table('architecture_snapshots')
    op.drop_table('architecture_versions')
