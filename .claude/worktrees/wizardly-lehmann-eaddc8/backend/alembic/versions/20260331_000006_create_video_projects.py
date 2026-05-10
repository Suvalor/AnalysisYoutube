from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260331_000006"
down_revision: Union[str, None] = "20260331_000005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "video_projects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="idea"),
        sa.Column("script_id", sa.Integer(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["script_id"], ["script_libraries.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_video_projects_id", "video_projects", ["id"])
    op.create_index("ix_video_projects_user_id", "video_projects", ["user_id"])
    op.create_index("ix_video_projects_status", "video_projects", ["status"])
    op.create_index("ix_video_projects_script_id", "video_projects", ["script_id"])


def downgrade() -> None:
    op.drop_index("ix_video_projects_script_id", table_name="video_projects")
    op.drop_index("ix_video_projects_status", table_name="video_projects")
    op.drop_index("ix_video_projects_user_id", table_name="video_projects")
    op.drop_index("ix_video_projects_id", table_name="video_projects")
    op.drop_table("video_projects")

