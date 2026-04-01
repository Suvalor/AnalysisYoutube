from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260401_000013"
down_revision: Union[str, None] = "20260401_000012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "model_libraries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("api_base_url", sa.String(length=512), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("supported_models_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_model_libraries_id"), "model_libraries", ["id"], unique=False)
    op.create_index(op.f("ix_model_libraries_user_id"), "model_libraries", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_model_libraries_user_id"), table_name="model_libraries")
    op.drop_index(op.f("ix_model_libraries_id"), table_name="model_libraries")
    op.drop_table("model_libraries")
