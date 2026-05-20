"""create keyword_history table

Revision ID: 20260520_000004
Revises: 20260520_000003
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa

revision = "20260520_000004"
down_revision = "20260520_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建 keyword_history 表，用于记录登录用户的关键词搜索历史。"""
    op.create_table(
        "keyword_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("keyword", sa.String(200), nullable=False),
        sa.Column("region", sa.String(5), nullable=False, server_default="US"),
        sa.Column("language", sa.String(10), nullable=False, server_default="zh"),
        sa.Column("search_volume", sa.Integer(), nullable=True),
        sa.Column("competition", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_keyword_history_user_id", "keyword_history", ["user_id"])
    op.create_index("ix_keyword_history_keyword", "keyword_history", ["keyword"])


def downgrade() -> None:
    """回滚：删除 keyword_history 表。"""
    op.drop_index("ix_keyword_history_keyword", table_name="keyword_history")
    op.drop_index("ix_keyword_history_user_id", table_name="keyword_history")
    op.drop_table("keyword_history")
