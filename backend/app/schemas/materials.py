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
    file_size: int | None = None
    created_at: datetime

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
    file_size: int | None = None
    created_at: datetime
    remove_watermark: bool = Field(default=False)
