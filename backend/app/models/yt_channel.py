from datetime import datetime

from sqlalchemy import BIGINT, DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class YtChannel(Base):
    """YouTube 频道数据."""

    __tablename__ = "yt_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    channel_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    thumbnail_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    subscriber_count: Mapped[int] = mapped_column(BIGINT, nullable=False, default=0)
    video_count: Mapped[int] = mapped_column(BIGINT, nullable=False, default=0)
    view_count: Mapped[int] = mapped_column(BIGINT, nullable=False, default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

