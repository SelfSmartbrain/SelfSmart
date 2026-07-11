"""Phase 11 capabilities

Revision ID: 010_phase11_capabilities
Revises: 009_phase10g_evolution
Create Date: 2026-06-14 18:05:38.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010_phase11_capabilities'
down_revision = '009_phase10g_evolution'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'capability_scores',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('model_id', sa.UUID(), nullable=False),
        sa.Column('capability_type', sa.String(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table(
        'capability_growth_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('capability_id', sa.UUID(), nullable=False),
        sa.Column('previous_score', sa.Float(), nullable=False),
        sa.Column('new_score', sa.Float(), nullable=False),
        sa.Column('growth_rate', sa.Float(), nullable=False),
        sa.Column('measured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('catalyst', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'transfer_learning_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source_capability', sa.String(), nullable=False),
        sa.Column('target_capability', sa.String(), nullable=False),
        sa.Column('transfer_efficiency', sa.Float(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('parameters_transferred', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'discovery_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('discovery_type', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('novelty_score', sa.Float(), nullable=False),
        sa.Column('impact_score', sa.Float(), nullable=False),
        sa.Column('discovered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'peer_reviews',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('reviewer_model_id', sa.UUID(), nullable=False),
        sa.Column('target_model_id', sa.UUID(), nullable=False),
        sa.Column('review_type', sa.String(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('feedback', sa.Text(), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'research_programs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('objective', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('budget', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'capability_regressions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('capability_id', sa.UUID(), nullable=False),
        sa.Column('previous_score', sa.Float(), nullable=False),
        sa.Column('new_score', sa.Float(), nullable=False),
        sa.Column('regression_amount', sa.Float(), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cause_analysis', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('capability_regressions')
    op.drop_table('research_programs')
    op.drop_table('peer_reviews')
    op.drop_table('discovery_records')
    op.drop_table('transfer_learning_records')
    op.drop_table('capability_growth_records')
    op.drop_table('capability_scores')
