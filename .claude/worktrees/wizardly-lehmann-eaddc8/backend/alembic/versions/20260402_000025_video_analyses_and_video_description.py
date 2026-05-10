from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = "20260402_000025"
down_revision: Union[str, None] = "20260402_000024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    db_name = conn.execute(text("SELECT DATABASE()")).scalar()

    # -------- youtube_videos.description --------
    col_exists = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = :db
              AND table_name = 'youtube_videos'
              AND column_name = 'description'
            """
        ),
        {"db": db_name},
    ).scalar()

    if not col_exists:
        # MySQL 的 TEXT/BLOB/JSON 列不能设置 DEFAULT 值；因此先允许 NULL，
        # 再补齐历史数据为 ''，最后把列改为 NOT NULL。
        op.add_column("youtube_videos", sa.Column("description", sa.Text(), nullable=True))

    # 把历史 NULL 补成空字符串，保证后续可转为 NOT NULL。
    op.execute("UPDATE youtube_videos SET description = '' WHERE description IS NULL")

    # 改为 NOT NULL（不再使用 DEFAULT）。
    op.alter_column("youtube_videos", "description", existing_type=sa.Text(), nullable=False)

    # -------- video_analyses --------
    table_exists = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = :db
              AND table_name = 'video_analyses'
            """
        ),
        {"db": db_name},
    ).scalar()

    if not table_exists:
        op.create_table(
            "video_analyses",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("video_id", sa.Integer(), nullable=False, index=True),
            sa.Column("org_id", sa.Integer(), nullable=False, index=True),
            sa.Column("model_id", sa.String(length=128), nullable=False),
            sa.Column("agent_id", sa.Integer(), nullable=True),
            # MySQL 的 TEXT 列不能设置 DEFAULT，因此这里不使用 server_default。
            # 插入时由业务显式写入 content。
            sa.Column("content", sa.Text(), nullable=False),
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
            sa.ForeignKeyConstraint(["video_id"], ["youtube_videos.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("org_id", "video_id", name="uq_video_analyses_org_video"),
        )
        op.create_index("ix_video_analyses_video_id", "video_analyses", ["video_id"])
        op.create_index("ix_video_analyses_org_id", "video_analyses", ["org_id"])


def downgrade() -> None:
    op.drop_index("ix_video_analyses_org_id", table_name="video_analyses")
    op.drop_index("ix_video_analyses_video_id", table_name="video_analyses")
    op.drop_table("video_analyses")
    op.drop_column("youtube_videos", "description")

