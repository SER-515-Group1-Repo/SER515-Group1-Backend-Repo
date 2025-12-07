"""Create roles table and add role_code to users with defaults

Revision ID: b2d3e4f5g6h7
Revises: change_assignee_to_assignees
Create Date: 2025-12-06 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'b2d3e4f5g6h7'
down_revision: Union[str, Sequence[str], None] = 'change_assignee_to_assignees'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = inspect(conn)

    # Check if roles table already exists
    tables = inspector.get_table_names()

    if "roles" not in tables:
        # Create roles table
        op.create_table(
            "roles",
            sa.Column("code", sa.String(length=100), nullable=False),
            sa.Column("name", sa.String(length=250), nullable=False),
            sa.PrimaryKeyConstraint("code"),
        )
        # Create index on code column
        op.create_index(op.f("ix_roles_code"), "roles", ["code"])

        # Insert default roles
        op.execute(
            """
            INSERT INTO roles (code, name) VALUES
            ('product-manager', 'Product Manager'),
            ('stakeholder', 'Stakeholder'),
            ('dev-team', 'Dev Team'),
            ('scrum-master', 'Scrum Master')
            """
        )

    # Add role_code column to users table if it doesn't exist
    columns = [c["name"] for c in inspector.get_columns("users")]

    if "role_code" not in columns:
        op.add_column(
            "users",
            sa.Column("role_code", sa.String(length=100), nullable=True)
        )
        # Add foreign key constraint
        op.create_foreign_key(
            "fk_users_role_code_roles_code",
            "users",
            "roles",
            ["role_code"],
            ["code"]
        )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = inspect(conn)

    # Drop foreign key from users table if it exists
    columns = [c["name"] for c in inspector.get_columns("users")]
    if "role_code" in columns:
        op.drop_constraint("fk_users_role_code_roles_code",
                           "users", type_="foreignkey")
        op.drop_column("users", "role_code")

    # Drop roles table if it exists
    tables = inspector.get_table_names()
    if "roles" in tables:
        op.drop_table("roles")
