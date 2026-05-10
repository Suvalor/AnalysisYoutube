from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class VideoHighlightCreate(BaseModel):
    start_sec: float = Field(..., ge=0, description="起始秒数")
    end_sec: float = Field(..., gt=0, description="结束秒数")
    label: str = Field(default="", max_length=100, description="片段标注")
    score: float = Field(default=0.5, ge=0, le=1, description="评分")


class VideoHighlightRead(BaseModel):
    id: int
    video_id: int
    user_id: int
    start_sec: float
    end_sec: float
    score: float
    label: str
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ExtractHighlightsResponse(BaseModel):
    highlights: list[VideoHighlightRead]
    message: str = ""
