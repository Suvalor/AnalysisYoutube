"""add protocol column to model_libraries

Revision ID: 20260425_000001
Revises: 20260423_000002
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa

revision = "20260425_000001"
down_revision = "20260423_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "model_libraries",
        sa.Column("protocol", sa.String(16), nullable=False, server_default="anthropic"),
    )


def downgrade() -> None:
    op.drop_column("model_libraries", "protocol")
