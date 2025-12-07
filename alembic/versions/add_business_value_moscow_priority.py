"""add_business_value_moscow_priority_to_stories

Revision ID: abcd1234_moscow
Revises: 1970463ad067
Create Date: 2025-01-XX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "abcd1234_moscow"
down_revision: Union[str, None] = "1970463ad067"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add moscow_priority column to stories table if it doesn't already exist."""
    conn = op.get_bind()
    inspector = inspect(conn)

    columns = [c["name"] for c in inspector.get_columns("stories")]

    if "moscow_priority" in columns:
        # Column already exists; don't try to add it again
        print("Column 'moscow_priority' already exists on 'stories'; skipping add_column.")
        return

    op.add_column(
        "stories",
        sa.Column("moscow_priority", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    """Remove moscow_priority column from stories table if it exists."""
    conn = op.get_bind()
    inspector = inspect(conn)

    columns = [c["name"] for c in inspector.get_columns("stories")]

    if "moscow_priority" in columns:
        op.drop_column("stories", "moscow_priority")
