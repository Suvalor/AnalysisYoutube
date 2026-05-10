"""create download_tasks table

Revision ID: 20260425_000002
Revises: 20260425_000001
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa

revision = "20260425_000002"
down_revision = "20260425_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "download_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.String(20), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("local_path", sa.String(500), nullable=False, server_default=""),
        sa.Column("error_message", sa.String(500), nullable=False, server_default=""),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_download_tasks_id"), "download_tasks", ["id"])
    op.create_index(op.f("ix_download_tasks_user_id"), "download_tasks", ["user_id"])
    op.create_index(op.f("ix_download_tasks_video_id"), "download_tasks", ["video_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_download_tasks_video_id"), table_name="download_tasks")
    op.drop_index(op.f("ix_download_tasks_user_id"), table_name="download_tasks")
    op.drop_index(op.f("ix_download_tasks_id"), table_name="download_tasks")
    op.drop_table("download_tasks")
