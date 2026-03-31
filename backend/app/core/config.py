from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl
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
    access_token_expire_minutes: int = Field(60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    backend_cors_origins: List[AnyHttpUrl] = Field(
        default_factory=lambda: [AnyHttpUrl("http://localhost:5173")]
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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()

