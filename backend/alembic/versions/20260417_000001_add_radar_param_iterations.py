"""add radar_param_iterations table

Revision ID: 20260417_000001
Revises: 20260416_000035
Create Date: 2026-04-17
"""

from alembic import op
import sqlalchemy as sa

revision = "20260417_000001"
down_revision = "20260416_000035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "radar_param_iterations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("iteration_type", sa.String(20), nullable=False, server_default="auto"),
        sa.Column("scan_params", sa.JSON(), nullable=False),
        sa.Column("recommended_params", sa.JSON(), nullable=True),
        sa.Column("scan_result_summary", sa.JSON(), nullable=True),
        sa.Column("iteration_effect", sa.JSON(), nullable=True),
        sa.Column("is_applied", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_radar_param_iterations_id", "radar_param_iterations", ["id"])
    op.create_index("ix_radar_param_iterations_user_id", "radar_param_iterations", ["user_id"])
    op.create_index("ix_radar_param_iterations_org_id", "radar_param_iterations", ["org_id"])


def downgrade() -> None:
    op.drop_index("ix_radar_param_iterations_org_id")
    op.drop_index("ix_radar_param_iterations_user_id")
    op.drop_index("ix_radar_param_iterations_id")
    op.drop_table("radar_param_iterations")