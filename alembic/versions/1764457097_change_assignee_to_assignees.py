"""Change assignee to assignees (JSON array)

Revision ID: change_assignee_to_assignees
Revises: a1b2c3d4e5f6
Create Date: 2025-11-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'change_assignee_to_assignees'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new assignees column as JSON
    op.add_column('stories', sa.Column('assignees', sa.JSON(), nullable=True))
    
    # Migrate data from assignee to assignees (convert single string to array)
    op.execute("""
        UPDATE stories 
        SET assignees = JSON_ARRAY(assignee)
        WHERE assignee IS NOT NULL AND assignee != '' AND assignee != 'Unassigned'
    """)
    
    # Set empty array for Unassigned or NULL
    op.execute("""
        UPDATE stories 
        SET assignees = JSON_ARRAY()
        WHERE assignee IS NULL OR assignee = '' OR assignee = 'Unassigned'
    """)
    
    # Drop the old assignee column
    op.drop_column('stories', 'assignee')


def downgrade() -> None:
    # Add back assignee column
    op.add_column('stories', sa.Column('assignee', sa.String(250), nullable=True, server_default='Unassigned'))
    
    # Migrate first assignee back
    op.execute("""
        UPDATE stories 
        SET assignee = JSON_UNQUOTE(JSON_EXTRACT(assignees, '$[0]'))
        WHERE assignees IS NOT NULL AND JSON_LENGTH(assignees) > 0
    """)
    
    # Set Unassigned for empty arrays
    op.execute("""
        UPDATE stories 
        SET assignee = 'Unassigned'
        WHERE assignees IS NULL OR JSON_LENGTH(assignees) = 0
    """)
    
    # Drop assignees column
    op.drop_column('stories', 'assignees')
