"""LLM 对话历史 Pydantic schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class LLMConversationMessage(BaseModel):
    role: str = Field(..., pattern=r"^(system|user|assistant)$")
    content: str


class LLMConversationRead(BaseModel):
    id: int
    user_id: int
    entity_type: str
    entity_id: str
    role: str
    content: str
    turn: int
    model_name: str | None = None
    created_at: datetime
