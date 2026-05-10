"""feishu_docs 增加离线归档字段

Revision ID: 20260404_000031
Revises: 20260402_000030
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260404_000031"
down_revision: Union[str, None] = "20260402_000030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "feishu_docs",
        sa.Column("archive_status", sa.String(length=32), nullable=False, server_default="UNARCHIVED"),
    )
    op.add_column(
        "feishu_docs",
        sa.Column("archive_file_url", sa.String(length=2048), nullable=True),
    )
    op.add_column(
        "feishu_docs",
        sa.Column("archive_type", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("feishu_docs", "archive_type")
    op.drop_column("feishu_docs", "archive_file_url")
    op.drop_column("feishu_docs", "archive_status")
