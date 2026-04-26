from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DownloadRequest(BaseModel):
    video_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="YouTube 视频 ID 列表",
        json_schema_extra={"examples": [["dQw4w9WgXcQ"]]},
    )


class DownloadTaskRead(BaseModel):
    id: int
    video_id: str
    status: str
    local_path: str = ""
    error_message: str = ""
    file_size: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DownloadTaskListResponse(BaseModel):
    items: list[DownloadTaskRead]
    total: int
