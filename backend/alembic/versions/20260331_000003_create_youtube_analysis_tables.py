from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260331_000003"
down_revision: Union[str, None] = "20260331_000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "youtube_channels",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("yt_channel_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=1024), nullable=True),
        sa.Column("subscriber_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_views", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("video_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_youtube_channels_id", "youtube_channels", ["id"])
    op.create_index(
        "ix_youtube_channels_yt_channel_id",
        "youtube_channels",
        ["yt_channel_id"],
        unique=True,
    )

    op.create_table(
        "youtube_videos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("yt_video_id", sa.String(length=32), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=1024), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("view_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("like_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("comment_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["channel_id"], ["youtube_channels.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_youtube_videos_id", "youtube_videos", ["id"])
    op.create_index("ix_youtube_videos_channel_id", "youtube_videos", ["channel_id"])
    op.create_index("ix_youtube_videos_yt_video_id", "youtube_videos", ["yt_video_id"], unique=True)

    op.create_table(
        "user_competitor_pools",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("group_name", sa.String(length=100), nullable=False, server_default="默认分组"),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["channel_id"], ["youtube_channels.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "channel_id", name="uq_user_competitor_channel"),
    )
    op.create_index("ix_user_competitor_pools_id", "user_competitor_pools", ["id"])


def downgrade() -> None:
    op.drop_index("ix_user_competitor_pools_id", table_name="user_competitor_pools")
    op.drop_table("user_competitor_pools")

    op.drop_index("ix_youtube_videos_yt_video_id", table_name="youtube_videos")
    op.drop_index("ix_youtube_videos_channel_id", table_name="youtube_videos")
    op.drop_index("ix_youtube_videos_id", table_name="youtube_videos")
    op.drop_table("youtube_videos")

    op.drop_index("ix_youtube_channels_yt_channel_id", table_name="youtube_channels")
    op.drop_index("ix_youtube_channels_id", table_name="youtube_channels")
    op.drop_table("youtube_channels")

