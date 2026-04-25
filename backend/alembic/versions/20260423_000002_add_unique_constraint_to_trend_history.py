"""add unique constraint to trend_history

Revision ID: 20260423_000002
Revises: 20260423_000001
Create Date: 2026-04-23

"""
from alembic import op

revision = "20260423_000002"
down_revision = "20260423_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Deduplicate: keep only the latest row per (user_id, cache_date, region, category_id)
    op.execute("""
        DELETE th1 FROM trend_history th1
        INNER JOIN trend_history th2
        ON th1.user_id = th2.user_id
           AND th1.cache_date = th2.cache_date
           AND th1.region = th2.region
           AND th1.category_id = th2.category_id
           AND th1.id < th2.id
    """)
    op.create_unique_constraint(
        "uq_trend_history",
        "trend_history",
        ["user_id", "cache_date", "region", "category_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_trend_history", "trend_history", type_="unique")
