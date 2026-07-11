"""Phase 8: Swarm Orchestration

Revision ID: 013_phase8_swarm
Revises: 012_phase7_multimodal
Create Date: 2026-06-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '013_phase8_swarm'
down_revision: Union[str, None] = '012_phase7_multimodal'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create director_agents table
    op.create_table(
        'director_agents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='idle'),
        sa.Column('max_sub_orchestrators', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('current_sub_orchestrators', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('active_goals_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_goals_completed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_director_agents_status', 'director_agents', ['status'])
    op.create_index('ix_director_agents_created_at', 'director_agents', ['created_at'])

    # Create swarm_goals table
    op.create_table(
        'swarm_goals',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('director_id', sa.UUID(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('estimated_complexity', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('required_capabilities', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('resource_requirements', postgresql.JSONB(), nullable=True),
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('sub_task_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completed_sub_tasks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['director_id'], ['director_agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_swarm_goals_director', 'swarm_goals', ['director_id'])
    op.create_index('ix_swarm_goals_status', 'swarm_goals', ['status'])
    op.create_index('ix_swarm_goals_priority', 'swarm_goals', ['priority'])
    op.create_index('ix_swarm_goals_created_at', 'swarm_goals', ['created_at'])

    # Create swarm_sub_tasks table (without FK to sub_orchestrators initially)
    op.create_table(
        'swarm_sub_tasks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('goal_id', sa.UUID(), nullable=False),
        sa.Column('assigned_orchestrator_id', sa.UUID(), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('dependencies', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('estimated_duration', sa.Integer(), nullable=False, server_default='300'),
        sa.Column('actual_duration', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('progress', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('result', postgresql.JSONB(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['goal_id'], ['swarm_goals.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_swarm_sub_tasks_goal', 'swarm_sub_tasks', ['goal_id'])
    op.create_index('ix_swarm_sub_tasks_orchestrator', 'swarm_sub_tasks', ['assigned_orchestrator_id'])
    op.create_index('ix_swarm_sub_tasks_status', 'swarm_sub_tasks', ['status'])
    op.create_index('ix_swarm_sub_tasks_created_at', 'swarm_sub_tasks', ['created_at'])

    # Create sub_orchestrators table (without FK to swarm_sub_tasks initially)
    op.create_table(
        'sub_orchestrators',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('director_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='idle'),
        sa.Column('current_task_id', sa.UUID(), nullable=True),
        sa.Column('capabilities', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('current_load', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_capacity', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('total_tasks_completed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_task_duration', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('success_rate', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['director_id'], ['director_agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sub_orchestrators_director', 'sub_orchestrators', ['director_id'])
    op.create_index('ix_sub_orchestrators_status', 'sub_orchestrators', ['status'])
    op.create_index('ix_sub_orchestrators_created_at', 'sub_orchestrators', ['created_at'])

    # Add circular FK constraints after both tables exist
    op.create_foreign_key('fk_swarm_sub_tasks_orchestrator', 'swarm_sub_tasks', 'sub_orchestrators', ['assigned_orchestrator_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_sub_orchestrators_current_task', 'sub_orchestrators', 'swarm_sub_tasks', ['current_task_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_index('ix_swarm_sub_tasks_created_at', table_name='swarm_sub_tasks')
    op.drop_index('ix_swarm_sub_tasks_status', table_name='swarm_sub_tasks')
    op.drop_index('ix_swarm_sub_tasks_orchestrator', table_name='swarm_sub_tasks')
    op.drop_index('ix_swarm_sub_tasks_goal', table_name='swarm_sub_tasks')
    op.drop_table('swarm_sub_tasks')
    
    op.drop_index('ix_sub_orchestrators_created_at', table_name='sub_orchestrators')
    op.drop_index('ix_sub_orchestrators_status', table_name='sub_orchestrators')
    op.drop_index('ix_sub_orchestrators_director', table_name='sub_orchestrators')
    op.drop_table('sub_orchestrators')
    
    op.drop_index('ix_swarm_goals_created_at', table_name='swarm_goals')
    op.drop_index('ix_swarm_goals_priority', table_name='swarm_goals')
    op.drop_index('ix_swarm_goals_status', table_name='swarm_goals')
    op.drop_index('ix_swarm_goals_director', table_name='swarm_goals')
    op.drop_table('swarm_goals')
    
    op.drop_index('ix_director_agents_created_at', table_name='director_agents')
    op.drop_index('ix_director_agents_status', table_name='director_agents')
    op.drop_table('director_agents')
