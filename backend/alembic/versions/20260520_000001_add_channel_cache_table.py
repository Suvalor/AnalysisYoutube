"""add channel_cache table

Revision ID: 20260520_000001
Revises: 20260519_000002
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa

revision = "20260520_000001"
down_revision = "20260519_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """新增 channel_cache 表，缓存频道统计数据以减少 YouTube API 重复调用。"""
    op.create_table(
        "channel_cache",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("avatar_url", sa.String(1024), nullable=True),
        sa.Column("subscriber_count", sa.BIGINT(), nullable=False, server_default="0"),
        sa.Column("video_count", sa.BIGINT(), nullable=False, server_default="0"),
        sa.Column("view_count", sa.BIGINT(), nullable=False, server_default="0"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("country", sa.String(10), nullable=True),
        sa.Column("custom_url", sa.String(255), nullable=True),
        sa.Column(
            "cached_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id", name="uq_channel_cache_channel_id"),
    )
    op.create_index("ix_channel_cache_id", "channel_cache", ["id"])
    op.create_index("ix_channel_cache_channel_id", "channel_cache", ["channel_id"])


def downgrade() -> None:
    """回滚：删除 channel_cache 表。"""
    op.drop_index("ix_channel_cache_channel_id", table_name="channel_cache")
    op.drop_index("ix_channel_cache_id", table_name="channel_cache")
    op.drop_table("channel_cache")
