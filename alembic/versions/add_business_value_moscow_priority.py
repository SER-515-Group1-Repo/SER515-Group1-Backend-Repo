"""add_business_value_moscow_priority_to_stories

Revision ID: add_business_value_moscow_priority
Revises: change_assignee_to_assignees
Create Date: 2025-01-XX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_business_value_moscow_priority'
down_revision: Union[str, None] = 'change_assignee_to_assignees'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add moscow_priority column to stories table
    op.add_column('stories', sa.Column('moscow_priority', sa.String(50), nullable=True))


def downgrade() -> None:
    # Remove column from stories table
    op.drop_column('stories', 'moscow_priority')

