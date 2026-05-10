from datetime import datetime, date
from enum import Enum

from pydantic import BaseModel, Field


class MaterialTypeEnum(str, Enum):
    image = "image"
    video = "video"


class MaterialRead(BaseModel):
    id: int
    title: str
    file_type: MaterialTypeEnum
    file_url: str
    source: str = Field(default="INSPIRATION", description="素材行来源标记")
    storage_platform: str = Field(default="aliyun", description="aliyun / tencent")
    storage_object_key: str | None = None
    file_size: int | None = None
    created_at: datetime
    access_url: str = Field(default="", description="展示用签名或回退 URL")

    model_config = {"from_attributes": True}


class MaterialsQuery(BaseModel):
    type: MaterialTypeEnum | None = None
    start_date: date | None = None
    end_date: date | None = None


class MaterialUploadResponse(BaseModel):
    id: int
    title: str
    file_type: MaterialTypeEnum
    file_url: str
    source: str = Field(default="INSPIRATION")
    storage_platform: str = Field(default="aliyun")
    storage_object_key: str | None = None
    file_size: int | None = None
    created_at: datetime
    remove_watermark: bool = Field(default=False)
    process_info: str = Field(
        default="",
        description="处理说明：未启用去水印、去水印已完成、或因环境等原因跳过去水印等",
    )
    access_url: str = Field(default="")


class MaterialAccessUrlResponse(BaseModel):
    """按素材行记录的 storage_platform 生成访问地址，不依赖全局开关。"""

    url: str
    mode: str = Field(description="presigned 或 public_fallback")
    expires_in: int | None = Field(default=None, description="签名 URL 有效秒数；公开回退时为 null")
