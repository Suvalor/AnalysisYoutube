"""游客会话模型。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class GuestSession(Base):
    """游客会话表：通过 Cookie guest_id 识别游客并记录每日配额使用量。"""

    __tablename__ = "guest_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    guest_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    daily_quotas: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment='{"youtube_api": int, "llm_api": int, "cv_api": int, "date": "YYYY-MM-DD"}',
    )
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )