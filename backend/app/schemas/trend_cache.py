from __future__ import annotations
from pydantic import BaseModel, Field


class TrendHistoryItem(BaseModel):
    id: int
    cache_date: str = Field(description="缓存日期 yyyy/MM/dd")
    region: str
    category_id: str = Field(default="", description="品类ID，空字符串表示全部")
    region_label: str = Field(description="地区中文名")
    category_label: str = Field(description="品类中文名")
    created_at: str


class TrendHistoryListResponse(BaseModel):
    items: list[TrendHistoryItem]
    total: int