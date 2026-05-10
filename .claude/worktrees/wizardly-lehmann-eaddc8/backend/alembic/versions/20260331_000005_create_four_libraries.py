from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = "20260331_000005"
down_revision: Union[str, None] = "20260331_000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prompt_libraries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_prompt_libraries_id", "prompt_libraries", ["id"])
    op.create_index("ix_prompt_libraries_user_id", "prompt_libraries", ["user_id"])

    op.create_table(
        "style_libraries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_style_libraries_id", "style_libraries", ["id"])
    op.create_index("ix_style_libraries_user_id", "style_libraries", ["user_id"])

    op.create_table(
        "asset_libraries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=20), nullable=False),
        sa.Column("file_url", sa.String(length=1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_asset_libraries_id", "asset_libraries", ["id"])
    op.create_index("ix_asset_libraries_user_id", "asset_libraries", ["user_id"])

    op.create_table(
        "script_libraries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", mysql.LONGTEXT(), nullable=False),
        sa.Column("prompt_id", sa.Integer(), nullable=True),
        sa.Column("style_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prompt_id"], ["prompt_libraries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["style_id"], ["style_libraries.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_script_libraries_id", "script_libraries", ["id"])
    op.create_index("ix_script_libraries_user_id", "script_libraries", ["user_id"])
    op.create_index("ix_script_libraries_prompt_id", "script_libraries", ["prompt_id"])
    op.create_index("ix_script_libraries_style_id", "script_libraries", ["style_id"])


def downgrade() -> None:
    op.drop_index("ix_script_libraries_style_id", table_name="script_libraries")
    op.drop_index("ix_script_libraries_prompt_id", table_name="script_libraries")
    op.drop_index("ix_script_libraries_user_id", table_name="script_libraries")
    op.drop_index("ix_script_libraries_id", table_name="script_libraries")
    op.drop_table("script_libraries")

    op.drop_index("ix_asset_libraries_user_id", table_name="asset_libraries")
    op.drop_index("ix_asset_libraries_id", table_name="asset_libraries")
    op.drop_table("asset_libraries")

    op.drop_index("ix_style_libraries_user_id", table_name="style_libraries")
    op.drop_index("ix_style_libraries_id", table_name="style_libraries")
    op.drop_table("style_libraries")

    op.drop_index("ix_prompt_libraries_user_id", table_name="prompt_libraries")
    op.drop_index("ix_prompt_libraries_id", table_name="prompt_libraries")
    op.drop_table("prompt_libraries")

