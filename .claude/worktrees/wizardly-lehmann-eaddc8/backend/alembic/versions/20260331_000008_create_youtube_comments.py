"""创建 youtube_comments 表

Revision ID: 20260331_000008
Revises: 20260331_000007
Create Date: 2026-03-31

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260331_000008"
down_revision: Union[str, None] = "20260331_000007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "youtube_comments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("yt_comment_id", sa.String(length=128), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("author_name", sa.String(length=255), nullable=False),
        sa.Column("author_avatar", sa.String(length=1024), nullable=True),
        sa.Column("text_original", sa.Text(), nullable=False),
        sa.Column("like_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("keyword_used", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["channel_id"], ["youtube_channels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["video_id"], ["youtube_videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("yt_comment_id", name="uq_youtube_comment_yt_id"),
    )
    op.create_index("ix_youtube_comments_id", "youtube_comments", ["id"])
    op.create_index("ix_youtube_comments_video_id", "youtube_comments", ["video_id"])
    op.create_index("ix_youtube_comments_channel_id", "youtube_comments", ["channel_id"])


def downgrade() -> None:
    op.drop_index("ix_youtube_comments_channel_id", table_name="youtube_comments")
    op.drop_index("ix_youtube_comments_video_id", table_name="youtube_comments")
    op.drop_index("ix_youtube_comments_id", table_name="youtube_comments")
    op.drop_table("youtube_comments")
