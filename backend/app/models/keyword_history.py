"""关键词研究历史模型：记录登录用户的关键词搜索历史。"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class KeywordHistory(Base):
    """关键词搜索历史：每次成功搜索后记录，支持用户回溯历史关键词。"""

    __tablename__ = "keyword_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    keyword: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(5), nullable=False, default="US")
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="zh")
    search_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    competition: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )
