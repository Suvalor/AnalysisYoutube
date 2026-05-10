"""add locale field to users

Revision ID: 20260419_000002
Revises: 20260419_000001
Create Date: 2026-04-19

"""
from alembic import op
import sqlalchemy as sa

revision = "20260419_000002"
down_revision = "20260419_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("locale", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "locale")
