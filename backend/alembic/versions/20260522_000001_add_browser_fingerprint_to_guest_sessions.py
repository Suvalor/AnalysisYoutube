"""add browser_fingerprint to guest_sessions

Revision ID: 20260522_000001
Revises: 20260520_000005
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260522_000001"
down_revision: Union[str, None] = "20260520_000005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "guest_sessions",
        sa.Column("browser_fingerprint", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_guest_sessions_browser_fingerprint",
        "guest_sessions",
        ["browser_fingerprint"],
    )


def downgrade() -> None:
    op.drop_index("ix_guest_sessions_browser_fingerprint", table_name="guest_sessions")
    op.drop_column("guest_sessions", "browser_fingerprint")
