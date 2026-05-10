"""LLM 对话历史模型：按业务实体隔离，支持多轮对话记忆。"""

from datetime import datetime, timezone

from sqlalchemy import Index, String, Text, Integer, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class LLMConversation(Base):
    __tablename__ = "llm_conversation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(
        SAEnum("system", "user", "assistant", name="llm_conversation_role"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    turn: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("idx_user_entity", "user_id", "entity_type", "entity_id"),
        Index("idx_entity_turn", "entity_type", "entity_id", "turn"),
    )
