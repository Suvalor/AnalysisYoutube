from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260401_000016"
down_revision: Union[str, None] = "20260401_000015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("script_libraries", sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("script_libraries", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_script_libraries_is_deleted"), "script_libraries", ["is_deleted"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_script_libraries_is_deleted"), table_name="script_libraries")
    op.drop_column("script_libraries", "deleted_at")
    op.drop_column("script_libraries", "is_deleted")
