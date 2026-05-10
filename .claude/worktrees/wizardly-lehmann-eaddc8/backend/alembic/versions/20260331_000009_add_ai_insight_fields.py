"""为 youtube_channels 和 youtube_videos 增加 AI 洞察字段

Revision ID: 20260331_000009
Revises: 20260331_000008
Create Date: 2026-03-31
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260331_000009"
down_revision: Union[str, None] = "20260331_000008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("youtube_channels", sa.Column("ai_tags", sa.JSON(), nullable=True))
    op.add_column("youtube_channels", sa.Column("ai_audience_age", sa.String(length=255), nullable=True))
    op.add_column("youtube_channels", sa.Column("ai_summary", sa.Text(), nullable=True))
    op.add_column("youtube_videos", sa.Column("tags", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("youtube_videos", "tags")
    op.drop_column("youtube_channels", "ai_summary")
    op.drop_column("youtube_channels", "ai_audience_age")
    op.drop_column("youtube_channels", "ai_tags")
