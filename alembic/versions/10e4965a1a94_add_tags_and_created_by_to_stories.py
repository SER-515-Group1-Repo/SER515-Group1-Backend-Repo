"""Add tags and created_by to stories

Revision ID: 10e4965a1a94
Revises: 6aa70ce08951
Create Date: 2025-11-20 15:06:11.283420
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '10e4965a1a94'
down_revision: Union[str, Sequence[str], None] = '6aa70ce08951'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = inspect(conn)

    # Get list of existing columns
    columns = [c["name"] for c in inspector.get_columns("stories")]

    # Add 'tags' if it doesn't exist
    if "tags" not in columns:
        op.add_column(
            "stories",
            sa.Column("tags", sa.String(length=500), nullable=True)
        )

    # Add 'created_by' if it doesn't exist
    if "created_by" not in columns:
        op.add_column(
            "stories",
            sa.Column("created_by", sa.String(length=250), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("stories")]

    # Drop columns only if they exist
    if "created_by" in columns:
        op.drop_column("stories", "created_by")

    if "tags" in columns:
        op.drop_column("stories", "tags")