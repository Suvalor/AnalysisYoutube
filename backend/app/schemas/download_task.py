from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, PrivateAttr, computed_field, model_validator


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
    video_title: str | None = None
    thumbnail_url: str | None = None
    status: str
    error_message: str = ""
    file_size: int = 0
    progress: float = 0
    created_at: datetime
    updated_at: datetime

    # Accepted from ORM objects but excluded from API output.
    local_path: str = Field(default="", exclude=True)
    # Private attribute used by has_file; populated from local_path.
    _local_path: str = PrivateAttr(default="")

    model_config = {"from_attributes": True}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_file(self) -> bool:
        """True when a local file exists for this task."""
        if not self._local_path:
            return False
        try:
            return Path(self._local_path).is_file()
        except (OSError, ValueError):
            return False

    @model_validator(mode="after")
    def _sync_local_path(self) -> DownloadTaskRead:
        self._local_path = self.local_path
        return self


class DownloadTaskListResponse(BaseModel):
    items: list[DownloadTaskRead]
    total: int