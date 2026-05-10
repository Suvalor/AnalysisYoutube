from typing import Any

from pydantic import BaseModel, Field


class JimengSubmitRequest(BaseModel):
    model_name: str = Field(..., min_length=1, max_length=255)
    prompt: str = Field(..., min_length=1, max_length=5000)
    negative_prompt: str | None = Field(default=None, max_length=5000)
    params: dict[str, Any] | None = None


class JimengQueryRequest(BaseModel):
    task_id: str = Field(..., min_length=1)


class JimengGenerateRequest(BaseModel):
    model_name: str = Field(..., min_length=1, max_length=255)
    prompt: str = Field(..., min_length=1, max_length=5000)
    negative_prompt: str | None = Field(default=None, max_length=5000)
    width: int | None = Field(default=None, ge=64, le=4096)
    height: int | None = Field(default=None, ge=64, le=4096)
    ratio: str | None = Field(default=None, max_length=32)
    extra: dict[str, Any] | None = None


class JimengTaskSubmitResponse(BaseModel):
    task_id: str
    raw: dict[str, Any]


class JimengTaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Any | None = None
    raw: dict[str, Any]
