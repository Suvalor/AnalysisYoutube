from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class AssetFileTypeEnum(str, Enum):
    image = "image"
    video = "video"
    audio = "audio"


class PromptCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)


class PromptUpdate(BaseModel):
    title: str | None = None
    content: str | None = None


class PromptRead(BaseModel):
    id: int
    user_id: int
    title: str
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StyleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)


class StyleUpdate(BaseModel):
    title: str | None = None
    content: str | None = None


class StyleRead(BaseModel):
    id: int
    user_id: int
    title: str
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ModelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    api_base_url: str = Field(..., min_length=1, max_length=512)
    api_key: str | None = Field(None, min_length=1, max_length=2048)
    supported_models_json: str | list[str | dict[str, str]] | None = None


class ModelUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    api_base_url: str | None = Field(None, min_length=1, max_length=512)
    api_key: str | None = Field(None, min_length=1, max_length=2048)
    supported_models_json: str | list[str | dict[str, str]] | None = None


class ModelRead(BaseModel):
    id: int
    user_id: int
    name: str
    api_base_url: str
    supported_models_json: str | None
    has_api_key: bool
    created_at: datetime
    updated_at: datetime


class AssetCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    file_type: AssetFileTypeEnum
    file_url: str = Field(..., min_length=1, max_length=1024)
    file_size: int | None = None
    source: str = Field(default="MANUAL", max_length=32, description="通常为 MANUAL")
    storage_platform: str = Field(default="aliyun", max_length=32, description="aliyun / tencent")
    storage_object_key: str | None = Field(None, max_length=512)


class AssetUpdate(BaseModel):
    title: str | None = None
    file_type: AssetFileTypeEnum | None = None
    file_url: str | None = None
    file_size: int | None = None


class AssetRead(BaseModel):
    id: int
    user_id: int
    title: str
    file_type: AssetFileTypeEnum
    file_url: str
    source: str = Field(default="MANUAL", description="MANUAL / SOP / INSPIRATION")
    storage_platform: str = Field(default="aliyun")
    storage_object_key: str | None = None
    file_size: int | None = None
    created_at: datetime
    updated_at: datetime
    access_url: str = Field(default="", description="列表/展示用签名或回退 URL（自定义域名 Host）")

    model_config = {"from_attributes": True}


class AssetListResponse(BaseModel):
    """素材库分页列表。"""

    items: list[AssetRead]
    total: int
    page: int
    page_size: int
    sort_by: Literal["created_at", "file_size"] = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"


class AssetPresignUploadRequest(BaseModel):
    """前端直传前向服务端申请 PUT 预签名参数。"""

    filename: str = Field(..., min_length=1, max_length=512)
    content_type: str | None = Field(None, max_length=255, description="MIME，须与浏览器 PUT 时 Content-Type 一致")
    module: Literal["MANUAL", "SOP", "INSPIRATION"] = Field(
        default="MANUAL",
        description="对应落库 source；须与组织当前 ACTIVE_STORAGE_PROVIDER 一致",
    )


class AssetPresignUploadResponse(BaseModel):
    upload_url: str = Field(..., description="浏览器对该 URL 发起 PUT，Body 为原始文件字节")
    final_access_url: str = Field(..., description="写入 asset_libraries.file_url 的访问根路径（含自定义域名）")
    storage_platform: str
    storage_object_key: str
    file_type: AssetFileTypeEnum
    expires_in: int
    method: Literal["PUT"] = "PUT"
    required_headers: dict[str, str] = Field(default_factory=dict, description="PUT 时必须携带的请求头")


class AssetUploadResponse(BaseModel):
    """素材库直传：写入对象存储并落库 asset_libraries（与多云策略一致）。"""

    id: int
    title: str
    file_type: AssetFileTypeEnum
    file_url: str
    source: str = Field(default="MANUAL")
    storage_platform: str = Field(default="aliyun", description="aliyun / tencent")
    storage_object_key: str | None = None
    file_size: int | None = None
    created_at: datetime
    remove_watermark: bool = False
    access_url: str = Field(default="", description="与 file_url 同逻辑生成的可访问链接")


class AssetAccessUrlResponse(BaseModel):
    """按 storage_platform 生成访问地址（签名 URL 已替换自定义域名）。"""

    url: str
    mode: str = Field(description="presigned 或 public_fallback")
    expires_in: int | None = None


class ScriptCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    prompt_id: int | None = None
    style_id: int | None = None


class ScriptUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    prompt_id: int | None = None
    style_id: int | None = None


class ScriptRead(BaseModel):
    id: int
    user_id: int
    title: str
    content: str
    prompt_id: int | None
    style_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GenerateScriptStreamRequest(BaseModel):
    prompt_id: int
    style_id: int
    topic: str = Field(..., min_length=1, max_length=2000)

