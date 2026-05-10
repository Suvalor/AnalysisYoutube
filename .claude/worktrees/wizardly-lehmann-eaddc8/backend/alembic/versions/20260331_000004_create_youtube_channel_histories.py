from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260331_000004"
down_revision: Union[str, None] = "20260331_000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "youtube_channel_histories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("record_date", sa.Date(), nullable=False),
        sa.Column("subscriber_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_views", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("video_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["channel_id"], ["youtube_channels.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("channel_id", "record_date", name="uq_channel_record_date"),
    )
    op.create_index("ix_youtube_channel_histories_id", "youtube_channel_histories", ["id"])
    op.create_index(
        "ix_youtube_channel_histories_channel_id",
        "youtube_channel_histories",
        ["channel_id"],
    )
    op.create_index(
        "ix_youtube_channel_histories_record_date",
        "youtube_channel_histories",
        ["record_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_youtube_channel_histories_record_date", table_name="youtube_channel_histories")
    op.drop_index("ix_youtube_channel_histories_channel_id", table_name="youtube_channel_histories")
    op.drop_index("ix_youtube_channel_histories_id", table_name="youtube_channel_histories")
    op.drop_table("youtube_channel_histories")

