from datetime import date, datetime
from sqlalchemy import Integer, String, Text, Date, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base_class import Base


class TrendCache(Base):
    __tablename__ = "trend_cache"
    __table_args__ = (
        UniqueConstraint("cache_date", "region", "category_id", name="uq_trend_cache"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cache_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(5), nullable=False, index=True)
    category_id: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    data: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TrendHistory(Base):
    __tablename__ = "trend_history"
    __table_args__ = (
        UniqueConstraint("user_id", "cache_date", "region", "category_id", name="uq_trend_history"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cache_date: Mapped[date] = mapped_column(Date, nullable=False)
    region: Mapped[str] = mapped_column(String(5), nullable=False)
    category_id: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    region_label: Mapped[str] = mapped_column(String(50), nullable=False)
    category_label: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
