"""Phase 7: Multi-Modal Context

Revision ID: 012_phase7_multimodal
Revises: 011_phase12_projects
Create Date: 2026-06-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '012_phase7_multimodal'
down_revision: Union[str, None] = '011_phase12_projects'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create screenshots table
    op.create_table(
        'screenshots',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=True),
        sa.Column('task_id', sa.UUID(), nullable=True),
        sa.Column('url', sa.String(length=2048), nullable=True),
        sa.Column('image_hash', sa.String(length=64), nullable=False),
        sa.Column('file_path', sa.String(length=512), nullable=True),
        sa.Column('viewport_width', sa.Integer(), nullable=False, server_default='1920'),
        sa.Column('viewport_height', sa.Integer(), nullable=False, server_default='1080'),
        sa.Column('analysis_status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('analyzed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_screenshots_session', 'screenshots', ['session_id'])
    op.create_index('ix_screenshots_task', 'screenshots', ['task_id'])
    op.create_index('ix_screenshots_created_at', 'screenshots', ['created_at'])
    op.create_index('ix_screenshots_image_hash', 'screenshots', ['image_hash'])

    # Create visual_elements table
    op.create_table(
        'visual_elements',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('screenshot_id', sa.UUID(), nullable=False),
        sa.Column('element_type', sa.String(length=100), nullable=False),
        sa.Column('bbox_x1', sa.Integer(), nullable=False),
        sa.Column('bbox_y1', sa.Integer(), nullable=False),
        sa.Column('bbox_x2', sa.Integer(), nullable=False),
        sa.Column('bbox_y2', sa.Integer(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('text_content', sa.Text(), nullable=True),
        sa.Column('attributes', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['screenshot_id'], ['screenshots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_visual_elements_screenshot', 'visual_elements', ['screenshot_id'])
    op.create_index('ix_visual_elements_type', 'visual_elements', ['element_type'])

    # Create interaction_logs table
    op.create_table(
        'interaction_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('screenshot_id', sa.UUID(), nullable=True),
        sa.Column('session_id', sa.UUID(), nullable=True),
        sa.Column('task_id', sa.UUID(), nullable=True),
        sa.Column('action_type', sa.String(length=100), nullable=False),
        sa.Column('element_id', sa.UUID(), nullable=True),
        sa.Column('coordinates_x', sa.Integer(), nullable=True),
        sa.Column('coordinates_y', sa.Integer(), nullable=True),
        sa.Column('text_input', sa.Text(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['screenshot_id'], ['screenshots.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['element_id'], ['visual_elements.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_interaction_logs_screenshot', 'interaction_logs', ['screenshot_id'])
    op.create_index('ix_interaction_logs_session', 'interaction_logs', ['session_id'])
    op.create_index('ix_interaction_logs_created_at', 'interaction_logs', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_interaction_logs_created_at', table_name='interaction_logs')
    op.drop_index('ix_interaction_logs_session', table_name='interaction_logs')
    op.drop_index('ix_interaction_logs_screenshot', table_name='interaction_logs')
    op.drop_table('interaction_logs')
    
    op.drop_index('ix_visual_elements_type', table_name='visual_elements')
    op.drop_index('ix_visual_elements_screenshot', table_name='visual_elements')
    op.drop_table('visual_elements')
    
    op.drop_index('ix_screenshots_image_hash', table_name='screenshots')
    op.drop_index('ix_screenshots_created_at', table_name='screenshots')
    op.drop_index('ix_screenshots_task', table_name='screenshots')
    op.drop_index('ix_screenshots_session', table_name='screenshots')
    op.drop_table('screenshots')
