from datetime import datetime

from pydantic import BaseModel, Field


class InspirationCreate(BaseModel):
    """新建灵感：content 即「think」正文。"""

    content: str = Field(..., min_length=1, max_length=200_000, description="灵感内容")
    source: str = Field(default="", max_length=255, description="灵感来源")
    recorded_at: datetime | None = Field(
        default=None,
        description="记录时间（前端 DatePicker）；不传则使用服务端当前时间",
    )


class InspirationUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=200_000)
    source: str | None = Field(default=None, max_length=255)
    recorded_at: datetime | None = None
    status: str | None = Field(default=None, max_length=64)


class InspirationLinkPlotBody(BaseModel):
    """剧情拆解保存成功后，将灵感关联到 sop_scripts 主键。"""

    plot_id: int = Field(..., ge=1, description="sop_scripts.id")


class InspirationRead(BaseModel):
    id: int
    user_id: int
    content: str
    source: str
    recorded_at: datetime
    status: str
    plot_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
