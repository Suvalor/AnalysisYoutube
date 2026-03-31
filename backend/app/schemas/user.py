from pydantic import BaseModel, Field


class UserSettingsRead(BaseModel):
    """当前用户设置返回体."""

    feishu_doc_url: str | None = Field(
        None,
        description="飞书云文档工作台链接",
    )


class UserSettingsUpdate(BaseModel):
    """更新当前用户设置请求体."""

    feishu_doc_url: str | None = Field(
        None,
        description="飞书云文档工作台链接",
    )

