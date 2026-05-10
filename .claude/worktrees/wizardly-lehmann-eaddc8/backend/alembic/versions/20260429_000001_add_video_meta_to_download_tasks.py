"""add video_title and thumbnail_url to download_tasks

Revision ID: 20260429_000001
Revises: 20260428_000001
Create Date: 2026-04-29
"""
from alembic import op
import sqlalchemy as sa

revision = "20260429_000001"
down_revision = "20260428_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "download_tasks",
        sa.Column("video_title", sa.String(500), nullable=True),
    )
    op.add_column(
        "download_tasks",
        sa.Column("thumbnail_url", sa.String(1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("download_tasks", "thumbnail_url")
    op.drop_column("download_tasks", "video_title")
