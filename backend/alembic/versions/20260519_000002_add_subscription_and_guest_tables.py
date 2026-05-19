"""add subscription_plans, user_subscriptions, admin_invitations, guest_sessions tables

Revision ID: 20260519_000002
Revises: 20260519_000001
Create Date: 2026-05-19
"""
from alembic import op
import sqlalchemy as sa

revision = "20260519_000002"
down_revision = "20260519_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """新增 4 张表：subscription_plans, user_subscriptions, admin_invitations, guest_sessions。"""
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("quotas_json", sa.JSON(), nullable=False),
        sa.Column("price_monthly", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW() ON UPDATE NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "user_subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_user_subscriptions_user_id", "user_subscriptions", ["user_id"])

    op.create_table(
        "admin_invitations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(6), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("used_by", sa.Integer(), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_admin_invitations_code"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["used_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_admin_invitations_created_by", "admin_invitations", ["created_by"])
    op.create_index("ix_admin_invitations_is_active", "admin_invitations", ["is_active"])

    op.create_table(
        "guest_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("guest_id", sa.String(36), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("daily_quotas", sa.JSON(), nullable=True),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("guest_id", name="uq_guest_sessions_guest_id"),
    )
    op.create_index("ix_guest_sessions_guest_id", "guest_sessions", ["guest_id"])


def downgrade() -> None:
    """回滚：删除索引和 4 张表。"""
    op.drop_index("ix_admin_invitations_is_active", table_name="admin_invitations")
    op.drop_index("ix_admin_invitations_created_by", table_name="admin_invitations")
    op.drop_table("guest_sessions")
    op.drop_table("admin_invitations")
    op.drop_table("user_subscriptions")
    op.drop_table("subscription_plans")
