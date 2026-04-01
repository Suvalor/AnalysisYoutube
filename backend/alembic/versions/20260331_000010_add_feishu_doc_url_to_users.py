from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260331_000010"
down_revision: Union[str, None] = "20260331_000009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("feishu_doc_url", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "feishu_doc_url")

