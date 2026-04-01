from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260401_000012"
down_revision: Union[str, None] = "20260331_000011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("ai_api_base_url", sa.String(length=512), nullable=True))
    op.add_column("users", sa.Column("ai_models_json", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("ai_prompt_config_json", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("ai_api_key_encrypted", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "ai_api_key_encrypted")
    op.drop_column("users", "ai_prompt_config_json")
    op.drop_column("users", "ai_models_json")
    op.drop_column("users", "ai_api_base_url")
