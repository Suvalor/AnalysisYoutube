"""add ip_address index to guest_sessions

Revision ID: 20260520_000003
Revises: 20260520_000002
Create Date: 2026-05-20
"""
from alembic import op

revision = "20260520_000003"
down_revision = "20260520_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """为 guest_sessions.ip_address 添加索引，加速按 IP 查找游客会话。"""
    op.create_index("ix_guest_sessions_ip_address", "guest_sessions", ["ip_address"])


def downgrade() -> None:
    """回滚：删除 ip_address 索引。"""
    op.drop_index("ix_guest_sessions_ip_address", table_name="guest_sessions")
