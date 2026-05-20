from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class FeishuDoc(Base):
    __tablename__ = "feishu_docs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    org_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # 离线归档：UNARCHIVED / ARCHIVING / SUCCESS / FAILED
    archive_status: Mapped[str] = mapped_column(String(32), nullable=False, default="UNARCHIVED", server_default="UNARCHIVED")
    archive_file_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    archive_type: Mapped[str | None] = mapped_column(String(16), nullable=True)

