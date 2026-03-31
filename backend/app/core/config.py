from functools import lru_cache
import json

from pydantic import Field
from pydantic import computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """全局配置，优先从环境变量读取。"""

    mysql_user: str = Field("root", alias="MYSQL_USER")
    mysql_password: str = Field("password", alias="MYSQL_PASSWORD")
    mysql_host: str = Field("127.0.0.1", alias="MYSQL_HOST")
    mysql_port: int = Field(3306, alias="MYSQL_PORT")
    mysql_db: str = Field("creator_saas", alias="MYSQL_DB")

    database_url: str | None = Field(None, alias="DATABASE_URL")

    secret_key: str = Field("change_me", alias="SECRET_KEY")
    algorithm: str = Field("HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    youtube_api_key: str = Field("", alias="YOUTUBE_API_KEY")
    volcengine_api_key: str = Field("", alias="VOLCENGINE_API_KEY")
    volcengine_endpoint_id: str = Field("", alias="VOLCENGINE_ENDPOINT_ID")
    volcengine_base_url: str = Field("", alias="VOLCENGINE_BASE_URL")
    aliyun_access_key_id: str = Field("", alias="ALIYUN_ACCESS_KEY_ID")
    aliyun_access_key_secret: str = Field("", alias="ALIYUN_ACCESS_KEY_SECRET")
    aliyun_role_arn: str = Field("", alias="ALIYUN_ROLE_ARN")
    aliyun_region_id: str = Field("", alias="ALIYUN_REGION_ID")
    aliyun_oss_bucket_name: str = Field("", alias="ALIYUN_OSS_BUCKET_NAME")
    aliyun_oss_endpoint: str = Field("", alias="ALIYUN_OSS_ENDPOINT")

    # 支持单个 URL、逗号分隔字符串，或 JSON 数组字符串
    backend_cors_origins: str = Field(
        "http://localhost:5173",
        alias="BACKEND_CORS_ORIGINS",
    )

    @computed_field  # type: ignore[misc]
    @property
    def sqlalchemy_database_uri(self) -> str:
        """返回 SQLAlchemy 使用的异步连接 URL。"""
        if self.database_url:
            return self.database_url
        return (
            f"mysql+asyncmy://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
        )

    @computed_field  # type: ignore[misc]
    @property
    def cors_origins(self) -> list[str]:
        """将 CORS 配置解析为 URL 列表。"""
        raw_value = self.backend_cors_origins.strip()
        if not raw_value:
            return []

        if raw_value.startswith("["):
            try:
                parsed = json.loads(raw_value)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                pass

        return [item.strip() for item in raw_value.split(",") if item.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()

