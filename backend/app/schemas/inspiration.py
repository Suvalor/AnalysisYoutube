from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class InspirationCreate(BaseModel):
    """新建灵感：content 为「think」正文；可与 image_url 组合，但至少其一有效。"""

    content: str = Field(default="", max_length=200_000, description="灵感文字，可与图片二选一")
    image_url: str | None = Field(default=None, max_length=1024, description="灵感图片 URL（通常来自素材上传接口）")
    source: str = Field(default="", max_length=255, description="灵感来源")
    recorded_at: datetime | None = Field(
        default=None,
        description="记录时间（前端 DatePicker）；不传则使用服务端当前时间",
    )

    @model_validator(mode="after")
    def require_text_or_image(self) -> InspirationCreate:
        has_text = bool(self.content.strip())
        has_image = bool((self.image_url or "").strip())
        if not has_text and not has_image:
            raise ValueError("须填写文字灵感或上传图片")
        return self


class InspirationUpdate(BaseModel):
    content: str | None = Field(default=None, max_length=200_000)
    image_url: str | None = Field(default=None, max_length=1024)
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
    image_url: str | None
    source: str
    recorded_at: datetime
    status: str
    plot_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
