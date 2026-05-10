from datetime import date, datetime
from sqlalchemy import Integer, String, Text, Date, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base_class import Base


class KeywordCache(Base):
    __tablename__ = "keyword_cache"
    __table_args__ = (
        UniqueConstraint("cache_date", "keyword", "region", "language", name="uq_keyword_cache"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cache_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    keyword: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(5), nullable=False, default="US")
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="zh")
    data: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
