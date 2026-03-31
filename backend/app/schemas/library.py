from datetime import datetime
from enum import Enum

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


class AssetCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    file_type: AssetFileTypeEnum
    file_url: str = Field(..., min_length=1, max_length=1024)


class AssetUpdate(BaseModel):
    title: str | None = None
    file_type: AssetFileTypeEnum | None = None
    file_url: str | None = None


class AssetRead(BaseModel):
    id: int
    user_id: int
    title: str
    file_type: AssetFileTypeEnum
    file_url: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


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

