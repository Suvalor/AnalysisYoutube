from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260401_000015"
down_revision: Union[str, None] = "20260401_000014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("youtube_access_token_encrypted", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("youtube_refresh_token_encrypted", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("youtube_token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("youtube_channel_id", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "youtube_channel_id")
    op.drop_column("users", "youtube_token_expires_at")
    op.drop_column("users", "youtube_refresh_token_encrypted")
    op.drop_column("users", "youtube_access_token_encrypted")
