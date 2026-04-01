"""youtube_channels 增加 ai_expertise（擅长内容）

Revision ID: 20260402_000017
Revises: 20260401_000016
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260402_000017"
down_revision: Union[str, None] = "20260401_000016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("youtube_channels", sa.Column("ai_expertise", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("youtube_channels", "ai_expertise")
