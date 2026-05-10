"""asset_libraries.source；sop 存储键；灵感 image_asset_id

Revision ID: 20260402_000024
Revises: 20260402_000023
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260402_000024"
down_revision: Union[str, None] = "20260402_000023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "asset_libraries",
        sa.Column("source", sa.String(length=32), nullable=False, server_default="MANUAL"),
    )
    op.add_column("sop_assets", sa.Column("storage_platform", sa.String(length=32), nullable=True))
    op.add_column("sop_assets", sa.Column("storage_object_key", sa.String(length=512), nullable=True))
    op.add_column("sop_media", sa.Column("storage_platform", sa.String(length=32), nullable=True))
    op.add_column("sop_media", sa.Column("storage_object_key", sa.String(length=512), nullable=True))
    op.add_column("inspirations", sa.Column("image_asset_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_inspirations_image_asset_id",
        "inspirations",
        "asset_libraries",
        ["image_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_inspirations_image_asset_id", "inspirations", type_="foreignkey")
    op.drop_column("inspirations", "image_asset_id")
    op.drop_column("sop_media", "storage_object_key")
    op.drop_column("sop_media", "storage_platform")
    op.drop_column("sop_assets", "storage_object_key")
    op.drop_column("sop_assets", "storage_platform")
    op.drop_column("asset_libraries", "source")
