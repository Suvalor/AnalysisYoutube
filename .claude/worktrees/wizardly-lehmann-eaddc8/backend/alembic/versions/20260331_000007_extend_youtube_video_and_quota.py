from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260331_000007"
down_revision: Union[str, None] = "20260331_000006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("youtube_videos", sa.Column("duration_sec", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("youtube_videos", sa.Column("duration_str", sa.String(length=20), nullable=False, server_default="00:00"))
    op.add_column("youtube_videos", sa.Column("definition", sa.String(length=20), nullable=False, server_default="sd"))
    op.add_column("youtube_videos", sa.Column("privacy_status", sa.String(length=20), nullable=False, server_default="public"))
    op.add_column("youtube_videos", sa.Column("category_id", sa.String(length=20), nullable=True))

    op.create_table(
        "api_quota_usages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("record_date", sa.Date(), nullable=False),
        sa.Column("points_used", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("record_date", name="uq_api_quota_record_date"),
    )
    op.create_index("ix_api_quota_usages_id", "api_quota_usages", ["id"])
    op.create_index("ix_api_quota_usages_record_date", "api_quota_usages", ["record_date"])


def downgrade() -> None:
    op.drop_index("ix_api_quota_usages_record_date", table_name="api_quota_usages")
    op.drop_index("ix_api_quota_usages_id", table_name="api_quota_usages")
    op.drop_table("api_quota_usages")

    op.drop_column("youtube_videos", "category_id")
    op.drop_column("youtube_videos", "privacy_status")
    op.drop_column("youtube_videos", "definition")
    op.drop_column("youtube_videos", "duration_str")
    op.drop_column("youtube_videos", "duration_sec")

