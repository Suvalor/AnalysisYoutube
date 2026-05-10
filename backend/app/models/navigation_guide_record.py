"""出海导航推荐记录模型。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class NavigationGuideRecord(Base):
    """出海导航推荐记录：每次深度推荐后自动保存请求参数+完整结果，支持历史查阅。"""

    __tablename__ = "navigation_guide_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    org_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # 推荐请求参数快照
    request_params: Mapped[dict] = mapped_column(JSON, nullable=False)
    # 完整推荐结果（recommendations + avoid_niche + ai_summary + channel_info）
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
