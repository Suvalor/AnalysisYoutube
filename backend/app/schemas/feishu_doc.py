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
    archive_status: str = "UNARCHIVED"
    archive_file_url: str | None = None
    archive_type: str | None = None

    model_config = {"from_attributes": True}


class FeishuDocArchiveTriggerResponse(BaseModel):
    """触发归档或幂等响应。"""

    status: str = Field(..., description="accepted | already_archived")
    doc_id: int
    message: str | None = None


class FeishuDocListResponse(BaseModel):
    items: list[FeishuDocRead]
    total: int
    page: int
    page_size: int

