"""配额使用与检查 Pydantic Schema。"""

from pydantic import BaseModel, Field


class QuotaUsageRead(BaseModel):
    """当前用户配额使用情况返回体。"""

    role: str = Field(..., description="用户角色")
    youtube_api_used: int = Field(0, description="今日已用 YouTube API 配额")
    youtube_api_limit: int = Field(0, description="YouTube API 每日限额")
    llm_api_used: int = Field(0, description="今日已用 LLM API 配额")
    llm_api_limit: int = Field(0, description="LLM API 每日限额")
    cv_api_used: int = Field(0, description="今日已用 CV API 配额")
    cv_api_limit: int = Field(0, description="CV API 每日限额")


class QuotaCheck(BaseModel):
    """配额检查请求体。"""

    api_type: str = Field(
        ..., description="API 类型：youtube_api / llm_api / cv_api",
    )