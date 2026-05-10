"""script_libraries 增加 is_pinned（知识库置顶）

Revision ID: 20260404_000033
Revises: 20260404_000032
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260404_000033"
down_revision: Union[str, None] = "20260404_000032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "script_libraries",
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.create_index("ix_script_libraries_is_pinned", "script_libraries", ["is_pinned"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_script_libraries_is_pinned", table_name="script_libraries")
    op.drop_column("script_libraries", "is_pinned")
