from datetime import date, datetime

from pydantic import BaseModel, Field


class VideoProjectStatus:
    idea = "idea"
    scripting = "scripting"
    shooting = "shooting"
    editing = "editing"
    completed = "completed"


VALID_STATUSES = {
    VideoProjectStatus.idea,
    VideoProjectStatus.scripting,
    VideoProjectStatus.shooting,
    VideoProjectStatus.editing,
    VideoProjectStatus.completed,
}


class VideoProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    status: str = Field(default=VideoProjectStatus.idea)
    script_id: int | None = None
    due_date: date | None = None


class VideoProjectUpdate(BaseModel):
    title: str | None = None
    status: str | None = None
    script_id: int | None = None
    due_date: date | None = None


class VideoProjectRead(BaseModel):
    id: int
    user_id: int
    title: str
    status: str
    script_id: int | None
    due_date: date | None
    order_index: int
    created_at: datetime

    model_config = {"from_attributes": True}


class VideoProjectReorderItem(BaseModel):
    id: int
    status: str
    order_index: int

