"""add llm_conversation table

Revision ID: 20260416_000035
Revises: 20260404_000034
Create Date: 2026-04-16
"""

from alembic import op
import sqlalchemy as sa

revision = "20260416_000035"
down_revision = "20260404_000034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_conversation",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column(
            "role",
            sa.Enum("system", "user", "assistant", name="llm_conversation_role"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("turn", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model_name", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_user_entity",
        "llm_conversation",
        ["user_id", "entity_type", "entity_id"],
    )
    op.create_index(
        "idx_entity_turn",
        "llm_conversation",
        ["entity_type", "entity_id", "turn"],
    )


def downgrade() -> None:
    op.drop_index("idx_entity_turn", table_name="llm_conversation")
    op.drop_index("idx_user_entity", table_name="llm_conversation")
    op.drop_table("llm_conversation")
    op.execute("DROP TYPE IF EXISTS llm_conversation_role")
