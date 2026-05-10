"""add phone and email_verified to users

Revision ID: 20260417_000002
Revises: 20260417_000001
Create Date: 2026-04-17
"""

from alembic import op
import sqlalchemy as sa

revision = "20260417_000002"
down_revision = "20260417_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="0"))
    op.create_index("ix_users_phone", "users", ["phone"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_phone", table_name="users")
    op.drop_column("users", "email_verified")
    op.drop_column("users", "phone")
