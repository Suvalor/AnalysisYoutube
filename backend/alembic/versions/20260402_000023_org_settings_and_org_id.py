"""组织表、org_settings、用户归属组织；迁移原 user_integration_settings

Revision ID: 20260402_000023
Revises: 20260402_000022
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "20260402_000023"
down_revision: Union[str, None] = "20260402_000022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False, server_default="默认组织"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(sa.text("INSERT INTO organizations (id, name) VALUES (1, '默认组织')"))

    op.add_column("users", sa.Column("org_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_users_org_id", "users", "organizations", ["org_id"], ["id"], ondelete="RESTRICT")
    op.execute(sa.text("UPDATE users SET org_id = 1 WHERE org_id IS NULL"))
    op.alter_column(
        "users",
        "org_id",
        existing_type=sa.Integer(),
        nullable=False,
        server_default="1",
    )

    op.execute(
        sa.text(
            """
            CREATE TABLE org_settings (
                id INTEGER NOT NULL AUTO_INCREMENT,
                org_id INTEGER NOT NULL,
                payload_json LONGTEXT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                UNIQUE KEY uq_org_settings_org_id (org_id),
                KEY ix_org_settings_org_id (org_id),
                CONSTRAINT fk_org_settings_org_id
                    FOREIGN KEY (org_id) REFERENCES organizations (id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
    )

    conn = op.get_bind()
    insp = inspect(conn)
    if "user_integration_settings" in insp.get_table_names():
        conn.execute(
            sa.text(
                """
                INSERT INTO org_settings (org_id, payload_json, created_at, updated_at)
                SELECT 1, u.payload_json, u.created_at, u.updated_at
                FROM user_integration_settings AS u
                ORDER BY u.id DESC
                LIMIT 1
                """
            )
        )
        op.drop_index("ix_user_integration_settings_user_id", table_name="user_integration_settings")
        op.drop_table("user_integration_settings")


def downgrade() -> None:
    op.drop_index("ix_org_settings_org_id", table_name="org_settings")
    op.drop_table("org_settings")
    op.drop_constraint("fk_users_org_id", "users", type_="foreignkey")
    op.drop_column("users", "org_id")
    op.drop_table("organizations")
