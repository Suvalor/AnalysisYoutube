from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260401_000014"
down_revision: Union[str, None] = "20260401_000013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sop_scripts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("outline", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sop_scripts_id"), "sop_scripts", ["id"], unique=False)
    op.create_index(op.f("ix_sop_scripts_user_id"), "sop_scripts", ["user_id"], unique=False)
    op.create_index(op.f("ix_sop_scripts_status"), "sop_scripts", ["status"], unique=False)
    op.create_index(op.f("ix_sop_scripts_is_deleted"), "sop_scripts", ["is_deleted"], unique=False)

    op.create_table(
        "sop_segments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("script_id", sa.Integer(), nullable=False),
        sa.Column("segment_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["script_id"], ["sop_scripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sop_segments_id"), "sop_segments", ["id"], unique=False)
    op.create_index(op.f("ix_sop_segments_script_id"), "sop_segments", ["script_id"], unique=False)
    op.create_index(op.f("ix_sop_segments_status"), "sop_segments", ["status"], unique=False)
    op.create_index(op.f("ix_sop_segments_is_deleted"), "sop_segments", ["is_deleted"], unique=False)

    op.create_table(
        "sop_shots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("segment_id", sa.Integer(), nullable=False),
        sa.Column("shot_no", sa.Integer(), nullable=False),
        sa.Column("shot_type", sa.String(length=128), nullable=True),
        sa.Column("visual_prompt", sa.Text(), nullable=True),
        sa.Column("dialogue", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(6, 2), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["segment_id"], ["sop_segments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sop_shots_id"), "sop_shots", ["id"], unique=False)
    op.create_index(op.f("ix_sop_shots_segment_id"), "sop_shots", ["segment_id"], unique=False)
    op.create_index(op.f("ix_sop_shots_status"), "sop_shots", ["status"], unique=False)
    op.create_index(op.f("ix_sop_shots_is_deleted"), "sop_shots", ["is_deleted"], unique=False)

    op.create_table(
        "sop_assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("shot_id", sa.Integer(), nullable=False),
        sa.Column("source_asset_id", sa.Integer(), nullable=True),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("file_url", sa.String(length=1024), nullable=True),
        sa.Column("prompt_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["shot_id"], ["sop_shots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_asset_id"], ["sop_assets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sop_assets_id"), "sop_assets", ["id"], unique=False)
    op.create_index(op.f("ix_sop_assets_shot_id"), "sop_assets", ["shot_id"], unique=False)
    op.create_index(op.f("ix_sop_assets_source_asset_id"), "sop_assets", ["source_asset_id"], unique=False)
    op.create_index(op.f("ix_sop_assets_status"), "sop_assets", ["status"], unique=False)
    op.create_index(op.f("ix_sop_assets_is_deleted"), "sop_assets", ["is_deleted"], unique=False)

    op.create_table(
        "sop_media",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("shot_id", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(length=16), nullable=False),
        sa.Column("file_url", sa.String(length=1024), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(6, 2), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["shot_id"], ["sop_shots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sop_media_id"), "sop_media", ["id"], unique=False)
    op.create_index(op.f("ix_sop_media_shot_id"), "sop_media", ["shot_id"], unique=False)
    op.create_index(op.f("ix_sop_media_status"), "sop_media", ["status"], unique=False)
    op.create_index(op.f("ix_sop_media_is_deleted"), "sop_media", ["is_deleted"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sop_media_is_deleted"), table_name="sop_media")
    op.drop_index(op.f("ix_sop_media_status"), table_name="sop_media")
    op.drop_index(op.f("ix_sop_media_shot_id"), table_name="sop_media")
    op.drop_index(op.f("ix_sop_media_id"), table_name="sop_media")
    op.drop_table("sop_media")

    op.drop_index(op.f("ix_sop_assets_is_deleted"), table_name="sop_assets")
    op.drop_index(op.f("ix_sop_assets_status"), table_name="sop_assets")
    op.drop_index(op.f("ix_sop_assets_source_asset_id"), table_name="sop_assets")
    op.drop_index(op.f("ix_sop_assets_shot_id"), table_name="sop_assets")
    op.drop_index(op.f("ix_sop_assets_id"), table_name="sop_assets")
    op.drop_table("sop_assets")

    op.drop_index(op.f("ix_sop_shots_is_deleted"), table_name="sop_shots")
    op.drop_index(op.f("ix_sop_shots_status"), table_name="sop_shots")
    op.drop_index(op.f("ix_sop_shots_segment_id"), table_name="sop_shots")
    op.drop_index(op.f("ix_sop_shots_id"), table_name="sop_shots")
    op.drop_table("sop_shots")

    op.drop_index(op.f("ix_sop_segments_is_deleted"), table_name="sop_segments")
    op.drop_index(op.f("ix_sop_segments_status"), table_name="sop_segments")
    op.drop_index(op.f("ix_sop_segments_script_id"), table_name="sop_segments")
    op.drop_index(op.f("ix_sop_segments_id"), table_name="sop_segments")
    op.drop_table("sop_segments")

    op.drop_index(op.f("ix_sop_scripts_is_deleted"), table_name="sop_scripts")
    op.drop_index(op.f("ix_sop_scripts_status"), table_name="sop_scripts")
    op.drop_index(op.f("ix_sop_scripts_user_id"), table_name="sop_scripts")
    op.drop_index(op.f("ix_sop_scripts_id"), table_name="sop_scripts")
    op.drop_table("sop_scripts")
