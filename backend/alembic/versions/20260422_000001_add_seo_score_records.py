"""add seo_score_records table

Revision ID: 20260422_000001
Revises: 20260419_000003
Create Date: 2026-04-22

"""
from alembic import op
import sqlalchemy as sa

revision = "20260422_000001"
down_revision = "20260419_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "seo_score_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("thumbnail_url", sa.String(1024), nullable=True),
        sa.Column("target_keyword", sa.String(200), nullable=True),
        sa.Column("total_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("title_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tags_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("thumbnail_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("suggestions", sa.JSON(), nullable=True),
        sa.Column("ai_benchmark", sa.JSON(), nullable=True),
        sa.Column("competitor_summary", sa.JSON(), nullable=True),
        sa.Column("score_breakdown", sa.JSON(), nullable=True),
        sa.Column("model_library_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_seo_score_records_id"), "seo_score_records", ["id"])
    op.create_index(op.f("ix_seo_score_records_user_id"), "seo_score_records", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_seo_score_records_user_id"), table_name="seo_score_records")
    op.drop_index(op.f("ix_seo_score_records_id"), table_name="seo_score_records")
    op.drop_table("seo_score_records")
