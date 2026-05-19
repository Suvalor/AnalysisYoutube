"""add role column to users table

Revision ID: 20260519_000001
Revises: 20260429_000001
Create Date: 2026-05-19
"""
from alembic import op
import sqlalchemy as sa

revision = "20260519_000001"
down_revision = "20260429_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """users 表新增 role 字段，枚举 guest/user/subscriber/admin，默认 user。"""
    role_enum = sa.Enum("guest", "user", "subscriber", "admin", name="userrole")
    role_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "users",
        sa.Column(
            "role",
            role_enum,
            nullable=False,
            server_default="user",
        ),
    )


def downgrade() -> None:
    """回滚：删除 role 列及枚举类型。"""
    op.drop_column("users", "role")
    role_enum = sa.Enum("guest", "user", "subscriber", "admin", name="userrole")
    role_enum.drop(op.get_bind(), checkfirst=True)
