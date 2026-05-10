"""add mix_tasks and video_highlights tables

Revision ID: 20260427_000001
Revises: 20260425_000002
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa

revision = "20260427_000001"
down_revision = "20260425_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mix_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("source_video_ids", sa.JSON(), nullable=True),
        sa.Column("audio_source_type", sa.String(16), nullable=False, server_default="tts"),
        sa.Column("audio_source_ref", sa.String(2000), nullable=False, server_default=""),
        sa.Column("aspect_ratio", sa.String(8), nullable=False, server_default="9:16"),
        sa.Column("use_highlights", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("output_path", sa.String(500), nullable=False, server_default=""),
        sa.Column("error_message", sa.String(500), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_mix_tasks_id"), "mix_tasks", ["id"])
    op.create_index(op.f("ix_mix_tasks_user_id"), "mix_tasks", ["user_id"])

    op.create_table(
        "video_highlights",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("start_sec", sa.Float(), nullable=False),
        sa.Column("end_sec", sa.Float(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("label", sa.String(100), nullable=False, server_default=""),
        sa.Column("source", sa.String(16), nullable=False, server_default="ai"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["video_id"], ["youtube_videos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_video_highlights_id"), "video_highlights", ["id"])
    op.create_index(op.f("ix_video_highlights_video_id"), "video_highlights", ["video_id"])
    op.create_index(op.f("ix_video_highlights_user_id"), "video_highlights", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_video_highlights_user_id"), table_name="video_highlights")
    op.drop_index(op.f("ix_video_highlights_video_id"), table_name="video_highlights")
    op.drop_index(op.f("ix_video_highlights_id"), table_name="video_highlights")
    op.drop_table("video_highlights")

    op.drop_index(op.f("ix_mix_tasks_user_id"), table_name="mix_tasks")
    op.drop_index(op.f("ix_mix_tasks_id"), table_name="mix_tasks")
    op.drop_table("mix_tasks")
