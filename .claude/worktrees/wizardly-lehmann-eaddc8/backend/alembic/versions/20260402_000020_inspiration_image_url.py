"""inspirations 表增加 image_url

Revision ID: 20260402_000020
Revises: 20260402_000019
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260402_000020"
down_revision: Union[str, None] = "20260402_000019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("inspirations", sa.Column("image_url", sa.String(length=1024), nullable=True))


def downgrade() -> None:
    op.drop_column("inspirations", "image_url")
