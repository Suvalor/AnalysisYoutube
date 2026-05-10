"""创建 inspirations 灵感池表

Revision ID: 20260402_000019
Revises: 20260402_000018
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260402_000019"
down_revision: Union[str, None] = "20260402_000018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "inspirations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="待处理"),
        sa.Column("plot_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["plot_id"], ["sop_scripts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inspirations_id"), "inspirations", ["id"], unique=False)
    op.create_index(op.f("ix_inspirations_user_id"), "inspirations", ["user_id"], unique=False)
    op.create_index(op.f("ix_inspirations_status"), "inspirations", ["status"], unique=False)
    op.create_index(op.f("ix_inspirations_plot_id"), "inspirations", ["plot_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_inspirations_plot_id"), table_name="inspirations")
    op.drop_index(op.f("ix_inspirations_status"), table_name="inspirations")
    op.drop_index(op.f("ix_inspirations_user_id"), table_name="inspirations")
    op.drop_index(op.f("ix_inspirations_id"), table_name="inspirations")
    op.drop_table("inspirations")
