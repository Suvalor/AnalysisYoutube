"""关键词研究历史 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class KeywordHistoryItem(BaseModel):
    """单条关键词搜索历史记录。"""

    id: int
    keyword: str
    region: str
    language: str
    search_volume: int | None = None
    competition: float | None = None
    created_at: datetime


class KeywordHistoryListResponse(BaseModel):
    """关键词搜索历史列表响应。"""

    items: list[KeywordHistoryItem]
    total: int = Field(description="总记录数")
