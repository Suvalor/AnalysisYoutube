"""add refresh_attempted_at to channel_cache

Revision ID: 20260520_000002
Revises: 20260520_000001
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa

revision = "20260520_000002"
down_revision = "20260520_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """为 channel_cache 表添加 refresh_attempted_at 列，用于防止短时间内重复刷新过期缓存。"""
    op.add_column(
        "channel_cache",
        sa.Column(
            "refresh_attempted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="最近一次刷新尝试时间，用于防止短时间内重复刷新",
        ),
    )


def downgrade() -> None:
    """回滚：移除 refresh_attempted_at 列。"""
    op.drop_column("channel_cache", "refresh_attempted_at")
