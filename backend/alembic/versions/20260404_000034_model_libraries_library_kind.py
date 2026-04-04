"""model_libraries：用途分类（对话 / 图像修复）"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260404_000034"
down_revision: Union[str, None] = "20260404_000033"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "model_libraries",
        sa.Column(
            "library_kind",
            sa.String(length=32),
            nullable=False,
            server_default="chat",
        ),
    )
    op.create_index(
        "ix_model_libraries_user_library_kind",
        "model_libraries",
        ["user_id", "library_kind"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_model_libraries_user_library_kind", table_name="model_libraries")
    op.drop_column("model_libraries", "library_kind")
