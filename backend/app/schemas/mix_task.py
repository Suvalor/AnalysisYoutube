from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MixRequest(BaseModel):
    video_ids: list[int] = Field(..., min_length=1, max_length=20, description="素材 ID 列表")
    narration_text: str | None = Field(default=None, max_length=2000, description="TTS 配音文案")
    audio_file_id: str | None = Field(default=None, description="已上传的音频素材 ID")
    aspect_ratio: str = Field(default="9:16", pattern=r"^(9:16|16:9)$")
    use_highlights: bool = Field(default=True, description="优先使用精彩片段")


class MixTaskRead(BaseModel):
    id: int
    user_id: int
    status: str
    source_video_ids: list[int] | None
    audio_source_type: str
    audio_source_ref: str
    aspect_ratio: str
    use_highlights: bool
    output_path: str
    error_message: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MixTaskListResponse(BaseModel):
    items: list[MixTaskRead]
    total: int
