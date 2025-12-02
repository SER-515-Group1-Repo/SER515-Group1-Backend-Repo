"""Add position column to stories

Revision ID: 937ef9278454
Revises: a1b2c3d4e5f6
Create Date: 2025-12-01 19:13:05.120699

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '937ef9278454'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "stories",
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("stories", "position")
    pass
