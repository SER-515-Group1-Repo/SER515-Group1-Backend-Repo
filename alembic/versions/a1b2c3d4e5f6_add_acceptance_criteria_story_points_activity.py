"""add_acceptance_criteria_story_points_activity_to_stories

Revision ID: a1b2c3d4e5f6
Revises: 10e4965a1a94
Create Date: 2025-11-21 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '10e4965a1a94'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to stories table
    op.add_column('stories', sa.Column('acceptance_criteria', sa.JSON(), nullable=True))
    op.add_column('stories', sa.Column('story_points', sa.Integer(), nullable=True))
    op.add_column('stories', sa.Column('activity', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove columns from stories table
    op.drop_column('stories', 'activity')
    op.drop_column('stories', 'story_points')
    op.drop_column('stories', 'acceptance_criteria')
