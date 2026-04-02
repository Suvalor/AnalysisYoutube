from datetime import datetime

from pydantic import BaseModel, Field


class FeishuDocCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="文档名称")
    url: str = Field(..., min_length=1, max_length=1024, description="飞书分享链接")


class FeishuDocRead(BaseModel):
    id: int
    title: str
    url: str
    org_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class FeishuDocListResponse(BaseModel):
    items: list[FeishuDocRead]
    total: int
    page: int
    page_size: int

