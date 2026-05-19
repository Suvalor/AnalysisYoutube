"""订阅套餐模型。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class SubscriptionPlan(Base):
    """订阅套餐表：定义各套餐的配额与价格。"""

    __tablename__ = "subscription_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    quotas_json: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        comment='{"youtube_api": int, "llm_api": int, "cv_api": int}',
    )
    price_monthly: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False, server_default="0",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
