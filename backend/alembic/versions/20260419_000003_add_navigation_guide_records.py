"""add navigation_guide_records table

Revision ID: 20260419_000003
Revises: 20260419_000002
Create Date: 2026-04-19

"""
from alembic import op
import sqlalchemy as sa

revision = "20260419_000003"
down_revision = "20260419_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "navigation_guide_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("request_params", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_navigation_guide_records_id"), "navigation_guide_records", ["id"])
    op.create_index(op.f("ix_navigation_guide_records_user_id"), "navigation_guide_records", ["user_id"])
    op.create_index(op.f("ix_navigation_guide_records_org_id"), "navigation_guide_records", ["org_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_navigation_guide_records_org_id"), table_name="navigation_guide_records")
    op.drop_index(op.f("ix_navigation_guide_records_user_id"), table_name="navigation_guide_records")
    op.drop_index(op.f("ix_navigation_guide_records_id"), table_name="navigation_guide_records")
    op.drop_table("navigation_guide_records")