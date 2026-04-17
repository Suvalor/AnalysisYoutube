"""蓝海雷达参数迭代记录模型。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class RadarParamIteration(Base):
    """雷达参数迭代记录：每次复盘产出的推荐参数持久化，支持自动回填与效果追踪。"""

    __tablename__ = "radar_param_iterations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    org_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # auto=定时自动复盘, manual=用户手动触发
    iteration_type: Mapped[str] = mapped_column(String(20), nullable=False, default="auto")
    # 本次扫描使用的参数快照
    scan_params: Mapped[dict] = mapped_column(JSON, nullable=False)
    # AI 推荐的下一轮参数
    recommended_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 扫描结果摘要（命中数、平均爆款系数等）
    scan_result_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 与上一轮迭代的效果对比
    iteration_effect: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 是否已应用到下次扫描
    is_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
