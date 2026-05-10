"""add progress column to download_tasks

Revision ID: 20260428_000001
Revises: 20260427_000001
Create Date: 2026-04-28
"""
from alembic import op
import sqlalchemy as sa

revision = "20260428_000001"
down_revision = "20260427_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "download_tasks",
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("download_tasks", "progress")
