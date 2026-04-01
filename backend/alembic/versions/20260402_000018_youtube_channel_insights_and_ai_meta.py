"""youtube_channel_insights 表与频道 AI 溯源字段

Revision ID: 20260402_000018
Revises: 20260402_000017
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260402_000018"
down_revision: Union[str, None] = "20260402_000017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "youtube_channels",
        sa.Column("ai_analyzed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "youtube_channels",
        sa.Column("ai_source_model_library_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "youtube_channels",
        sa.Column("ai_source_llm_model_name", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "youtube_channels",
        sa.Column("ai_source_agent_id", sa.Integer(), nullable=True),
    )

    op.create_table(
        "youtube_channel_insights",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("model_library_id", sa.Integer(), nullable=True),
        sa.Column("llm_model_name", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("agent_id", sa.Integer(), nullable=True),
        sa.Column("ai_tags", sa.JSON(), nullable=True),
        sa.Column("ai_expertise", sa.Text(), nullable=True),
        sa.Column("ai_audience_age", sa.String(length=255), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["channel_id"], ["youtube_channels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_youtube_channel_insights_id"), "youtube_channel_insights", ["id"], unique=False)
    op.create_index(
        op.f("ix_youtube_channel_insights_channel_id"),
        "youtube_channel_insights",
        ["channel_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_youtube_channel_insights_channel_id"), table_name="youtube_channel_insights")
    op.drop_index(op.f("ix_youtube_channel_insights_id"), table_name="youtube_channel_insights")
    op.drop_table("youtube_channel_insights")
    op.drop_column("youtube_channels", "ai_source_agent_id")
    op.drop_column("youtube_channels", "ai_source_llm_model_name")
    op.drop_column("youtube_channels", "ai_source_model_library_id")
    op.drop_column("youtube_channels", "ai_analyzed_at")
