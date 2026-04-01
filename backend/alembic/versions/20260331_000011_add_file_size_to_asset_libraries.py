from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260331_000011"
down_revision: Union[str, None] = "20260331_000010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("asset_libraries", sa.Column("file_size", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("asset_libraries", "file_size")
