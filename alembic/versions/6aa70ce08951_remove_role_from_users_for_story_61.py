"""Remove role from users for Story 61

Revision ID: 6aa70ce08951
Revises: 1be4919f2147
Create Date: 2025-11-17 11:12:47.308698

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6aa70ce08951'
down_revision: Union[str, Sequence[str], None] = '1be4919f2147'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    """Remove role column from users (already done manually)."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    """Add role column back if needed."""
    op.add_column('users', sa.Column('role', sa.String(length=100), nullable=True))
    pass
