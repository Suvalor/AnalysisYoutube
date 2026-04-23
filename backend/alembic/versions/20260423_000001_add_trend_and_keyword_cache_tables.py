"""add trend_cache, trend_history, keyword_cache tables

Revision ID: 20260423_000001
Revises: 20260422_000001
Create Date: 2026-04-23

"""
from alembic import op
import sqlalchemy as sa

revision = "20260423_000001"
down_revision = "20260422_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trend_cache",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cache_date", sa.Date(), nullable=False),
        sa.Column("region", sa.String(5), nullable=False),
        sa.Column("category_id", sa.String(20), nullable=False, server_default=""),
        sa.Column("data", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cache_date", "region", "category_id", name="uq_trend_cache"),
    )
    op.create_index(op.f("ix_trend_cache_cache_date"), "trend_cache", ["cache_date"])
    op.create_index(op.f("ix_trend_cache_region"), "trend_cache", ["region"])

    op.create_table(
        "trend_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("cache_date", sa.Date(), nullable=False),
        sa.Column("region", sa.String(5), nullable=False),
        sa.Column("category_id", sa.String(20), nullable=False, server_default=""),
        sa.Column("region_label", sa.String(50), nullable=False),
        sa.Column("category_label", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trend_history_user_id"), "trend_history", ["user_id"])

    op.create_table(
        "keyword_cache",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cache_date", sa.Date(), nullable=False),
        sa.Column("keyword", sa.String(200), nullable=False),
        sa.Column("region", sa.String(5), nullable=False, server_default="US"),
        sa.Column("language", sa.String(10), nullable=False, server_default="zh"),
        sa.Column("data", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cache_date", "keyword", "region", "language", name="uq_keyword_cache"),
    )
    op.create_index(op.f("ix_keyword_cache_cache_date"), "keyword_cache", ["cache_date"])
    op.create_index(op.f("ix_keyword_cache_keyword"), "keyword_cache", ["keyword"])


def downgrade() -> None:
    op.drop_index(op.f("ix_keyword_cache_keyword"), table_name="keyword_cache")
    op.drop_index(op.f("ix_keyword_cache_cache_date"), table_name="keyword_cache")
    op.drop_table("keyword_cache")

    op.drop_index(op.f("ix_trend_history_user_id"), table_name="trend_history")
    op.drop_table("trend_history")

    op.drop_index(op.f("ix_trend_cache_region"), table_name="trend_cache")
    op.drop_index(op.f("ix_trend_cache_cache_date"), table_name="trend_cache")
    op.drop_table("trend_cache")