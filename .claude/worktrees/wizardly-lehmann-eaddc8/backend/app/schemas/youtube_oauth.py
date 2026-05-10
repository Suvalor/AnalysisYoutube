from datetime import datetime

from pydantic import BaseModel, Field


class YouTubeOAuthUrlResponse(BaseModel):
    auth_url: str
    state: str


class YouTubeOAuthCallbackRequest(BaseModel):
    code: str = Field(..., min_length=1)
    state: str | None = None
    redirect_uri: str | None = None


class YouTubeOAuthStatusResponse(BaseModel):
    connected: bool
    channel_id: str | None = None
    expires_at: datetime | None = None


class YouTubePublishRequest(BaseModel):
    media_url: str = Field(..., min_length=1, max_length=1024)
    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field("", max_length=5000)
    privacy_status: str = Field("private", pattern="^(private|public|unlisted)$")


class YouTubePublishResponse(BaseModel):
    status: str
    video_id: str | None = None
    message: str
