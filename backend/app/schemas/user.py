from pydantic import BaseModel, Field


class UserSettingsRead(BaseModel):
    """当前用户设置返回体（不含 API Key 明文）。"""

    feishu_doc_url: str | None = Field(
        None,
        description="飞书云文档工作台链接",
    )
    ai_api_base_url: str | None = Field(None, description="兼容 OpenAI 的 API 根地址")
    ai_models_json: str | None = Field(None, description="模型下拉 JSON 配置原文")
    ai_prompt_config_json: str | None = Field(None, description="提示词与风格等 JSON 配置原文")
    has_ai_api_key: bool = Field(False, description="是否已保存过 API Key（不返回明文）")
    theme: str | None = Field(None, description="用户主题偏好（light/liblib-dark/deep-blue/warm-orange）")


class UserSettingsUpdate(BaseModel):
    """更新当前用户设置请求体；未出现的字段表示不修改。"""

    feishu_doc_url: str | None = Field(
        None,
        description="飞书云文档工作台链接",
    )
    ai_api_base_url: str | None = Field(None, description="兼容 OpenAI 的 API 根地址，空字符串表示清空")
    ai_models_json: str | None = Field(None, description="模型列表 JSON；空字符串表示清空")
    ai_prompt_config_json: str | None = Field(None, description="提示词/风格 JSON；空字符串表示清空")
    ai_api_key: str | None = Field(
        None,
        description="仅当传入非空字符串时更新密钥；不传或 null 表示保留原密钥",
    )
    theme: str | None = Field(
        None,
        description="主题偏好（light/liblib-dark/deep-blue/warm-orange）；null 表示使用默认",
    )
