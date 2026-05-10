from __future__ import annotations
from pydantic import BaseModel, Field


class KeywordHistoryItem(BaseModel):
    id: int
    cache_date: str = Field(description="缓存日期 yyyy/MM/dd")
    keyword: str
    region: str
    language: str
    created_at: str


class KeywordHistoryListResponse(BaseModel):
    items: list[KeywordHistoryItem]
    total: int