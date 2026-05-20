"""feishu_docs 增加 user_id nullable 列 + 索引

Revision ID: 20260520_000005
Revises: 20260520_000004
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260520_000005"
down_revision: Union[str, None] = "20260520_000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "feishu_docs",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_feishu_docs_user_id", "feishu_docs", ["user_id"],
    )
    op.create_foreign_key(
        "fk_feishu_docs_user_id",
        "feishu_docs", "users",
        ["user_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_feishu_docs_user_id", "feishu_docs", type_="foreignkey")
    op.drop_index("ix_feishu_docs_user_id", table_name="feishu_docs")
    op.drop_column("feishu_docs", "user_id")
