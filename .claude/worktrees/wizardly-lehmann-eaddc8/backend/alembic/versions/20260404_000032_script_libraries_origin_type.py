"""script_libraries 增加 origin_type（区分 AI 工坊与手动录入）

Revision ID: 20260404_000032
Revises: 20260404_000031
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260404_000032"
down_revision: Union[str, None] = "20260404_000031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "script_libraries",
        sa.Column("origin_type", sa.String(length=32), nullable=False, server_default="AI_WORKSHOP"),
    )


def downgrade() -> None:
    op.drop_column("script_libraries", "origin_type")
