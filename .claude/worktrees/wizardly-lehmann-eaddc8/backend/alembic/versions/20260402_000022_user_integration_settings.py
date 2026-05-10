"""用户集成配置表（云存储、YouTube、火山等，JSON 持久化）

Revision ID: 20260402_000022
Revises: 20260402_000021

说明：MySQL 不允许 LONGTEXT 带 DEFAULT；部分 SQLAlchemy 版本仍会为 LONGTEXT 生成非法 DEFAULT，
因此本迁移对含 payload_json 的表使用原生 DDL，避免编译器注入默认值。
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260402_000022"
down_revision: Union[str, None] = "20260402_000021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            CREATE TABLE user_integration_settings (
                id INTEGER NOT NULL AUTO_INCREMENT,
                user_id INTEGER NOT NULL,
                payload_json LONGTEXT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                UNIQUE KEY uq_user_integration_settings_user_id (user_id),
                KEY ix_user_integration_settings_user_id (user_id),
                CONSTRAINT fk_user_integration_settings_user_id
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS user_integration_settings"))
