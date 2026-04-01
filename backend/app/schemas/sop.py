from datetime import datetime

from pydantic import BaseModel, Field


class SopScriptCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    outline: str | None = None
    status: str = Field(default="draft", max_length=32)


class SopScriptUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    outline: str | None = None
    status: str | None = Field(None, max_length=32)


class SopScriptRead(BaseModel):
    id: int
    user_id: int
    title: str
    outline: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SopSegmentCreate(BaseModel):
    script_id: int
    segment_no: int = 1
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    status: str = Field(default="draft", max_length=32)


class SopSegmentUpdate(BaseModel):
    segment_no: int | None = None
    title: str | None = Field(None, min_length=1, max_length=255)
    content: str | None = Field(None, min_length=1)
    status: str | None = Field(None, max_length=32)


class SopSegmentRead(BaseModel):
    id: int
    script_id: int
    segment_no: int
    title: str
    content: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SopShotCreate(BaseModel):
    segment_id: int
    shot_no: int = 1
    shot_type: str | None = Field(None, max_length=128)
    visual_prompt: str | None = None
    dialogue: str | None = None
    duration_seconds: float | None = None
    status: str = Field(default="draft", max_length=32)


class SopShotUpdate(BaseModel):
    shot_no: int | None = None
    shot_type: str | None = Field(None, max_length=128)
    visual_prompt: str | None = None
    dialogue: str | None = None
    duration_seconds: float | None = None
    status: str | None = Field(None, max_length=32)


class SopShotRead(BaseModel):
    id: int
    segment_id: int
    shot_no: int
    shot_type: str | None
    visual_prompt: str | None
    dialogue: str | None
    duration_seconds: float | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SopAssetCreate(BaseModel):
    shot_id: int
    source_asset_id: int | None = None
    asset_type: str = Field(default="image", max_length=32)
    name: str = Field(..., min_length=1, max_length=255)
    file_url: str | None = Field(None, max_length=1024)
    prompt_text: str | None = None
    status: str = Field(default="draft", max_length=32)


class SopAssetUpdate(BaseModel):
    source_asset_id: int | None = None
    asset_type: str | None = Field(None, max_length=32)
    name: str | None = Field(None, min_length=1, max_length=255)
    file_url: str | None = Field(None, max_length=1024)
    prompt_text: str | None = None
    status: str | None = Field(None, max_length=32)


class SopAssetRead(BaseModel):
    id: int
    shot_id: int
    source_asset_id: int | None
    asset_type: str
    name: str
    file_url: str | None
    prompt_text: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SopMediaCreate(BaseModel):
    shot_id: int
    media_type: str = Field(default="video", max_length=16)
    file_url: str | None = Field(None, max_length=1024)
    duration_seconds: float | None = None
    status: str = Field(default="pending", max_length=32)


class SopMediaUpdate(BaseModel):
    media_type: str | None = Field(None, max_length=16)
    file_url: str | None = Field(None, max_length=1024)
    duration_seconds: float | None = None
    status: str | None = Field(None, max_length=32)


class SopMediaRead(BaseModel):
    id: int
    shot_id: int
    media_type: str
    file_url: str | None
    duration_seconds: float | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SopAiSplitRequest(BaseModel):
    outline_markdown: str = Field(..., min_length=1)
    model: str | None = Field(None, min_length=1, max_length=128)


class SopAiSplitResponse(BaseModel):
    markdown: str


class SopAiSplitStartRequest(BaseModel):
    outline_markdown: str = Field(..., min_length=1)
    model: str | None = Field(None, min_length=1, max_length=128)


class SopAiSplitStartResponse(BaseModel):
    task_id: str
    status: str = "queued"


class SopShotsFromSegmentsRequest(BaseModel):
    script_id: int
    replace_existing: bool = True
