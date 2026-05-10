"""asset_libraries 增加 storage_platform / storage_object_key

Revision ID: 20260402_000021
Revises: 20260402_000020
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260402_000021"
down_revision: Union[str, None] = "20260402_000020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "asset_libraries",
        sa.Column("storage_platform", sa.String(length=32), nullable=False, server_default="aliyun"),
    )
    op.add_column(
        "asset_libraries",
        sa.Column("storage_object_key", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("asset_libraries", "storage_object_key")
    op.drop_column("asset_libraries", "storage_platform")
