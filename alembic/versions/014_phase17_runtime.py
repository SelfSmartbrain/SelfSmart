"""Phase 17: Runtime Completion & Production Readiness

Revision ID: 014_phase17_runtime
Revises: 013_phase8_swarm
Create Date: 2026-06-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '014_phase17_runtime'
down_revision: Union[str, None] = '013_phase8_swarm'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create objective_status enum
    objective_status_enum = postgresql.ENUM(
        'active', 'completed', 'blocked', 'failed', 'paused', 'cancelled',
        name='objective_status', create_type=False
    )
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'objective_status') THEN
                CREATE TYPE objective_status AS ENUM ('active', 'completed', 'blocked', 'failed', 'paused', 'cancelled');
            END IF;
        END
        $$;
    """)

    # Create objectives table
    op.create_table(
        'objectives',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('objective_id', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('priority', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('status', objective_status_enum, nullable=False, server_default=sa.text("'active'")),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('objective_id')
    )
    op.create_index('ix_objectives_status', 'objectives', ['status'])
    op.create_index('ix_objectives_priority', 'objectives', ['priority'])
    op.create_index('ix_objectives_created_at', 'objectives', ['created_at'])
    op.create_index('ix_objectives_objective_id', 'objectives', ['objective_id'])

    # Create objective_progress table
    op.create_table(
        'objective_progress',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('objective_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=100), nullable=False),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('result', postgresql.JSONB(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['objective_id'], ['objectives.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_objective_progress_objective', 'objective_progress', ['objective_id'])
    op.create_index('ix_objective_progress_status', 'objective_progress', ['status'])
    op.create_index('ix_objective_progress_timestamp', 'objective_progress', ['timestamp'])

    # Create objective_checkpoints table
    op.create_table(
        'objective_checkpoints',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('objective_id', sa.UUID(), nullable=False),
        sa.Column('checkpoint_name', sa.String(length=255), nullable=False),
        sa.Column('state_snapshot', postgresql.JSONB(), nullable=False),
        sa.Column('progress_snapshot', postgresql.JSONB(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['objective_id'], ['objectives.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_objective_checkpoints_objective', 'objective_checkpoints', ['objective_id'])
    op.create_index('ix_objective_checkpoints_created_at', 'objective_checkpoints', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_objective_checkpoints_created_at', table_name='objective_checkpoints')
    op.drop_index('ix_objective_checkpoints_objective', table_name='objective_checkpoints')
    op.drop_table('objective_checkpoints')

    op.drop_index('ix_objective_progress_timestamp', table_name='objective_progress')
    op.drop_index('ix_objective_progress_status', table_name='objective_progress')
    op.drop_index('ix_objective_progress_objective', table_name='objective_progress')
    op.drop_table('objective_progress')

    op.drop_index('ix_objectives_objective_id', table_name='objectives')
    op.drop_index('ix_objectives_created_at', table_name='objectives')
    op.drop_index('ix_objectives_priority', table_name='objectives')
    op.drop_index('ix_objectives_status', table_name='objectives')
    op.drop_table('objectives')

    op.execute("DROP TYPE IF EXISTS objective_status")
