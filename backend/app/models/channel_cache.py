"""频道统计数据缓存模型，减少 YouTube API 重复调用。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BIGINT, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class ChannelCache(Base):
    """缓存频道统计数据，避免对同一频道频繁调用 YouTube channels.list。"""

    __tablename__ = "channel_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    channel_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    subscriber_count: Mapped[int] = mapped_column(BIGINT, nullable=False, default=0)
    video_count: Mapped[int] = mapped_column(BIGINT, nullable=False, default=0)
    view_count: Mapped[int] = mapped_column(BIGINT, nullable=False, default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)
    custom_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    refresh_attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最近一次刷新尝试时间，用于防止短时间内重复刷新"
    )
