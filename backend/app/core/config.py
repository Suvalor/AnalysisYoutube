from functools import lru_cache
import json

from pydantic import Field, model_validator
from pydantic import computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """全局配置，优先从环境变量读取。"""

    mysql_user: str = Field("root", alias="MYSQL_USER")
    mysql_password: str = Field("", alias="MYSQL_PASSWORD")
    mysql_host: str = Field("127.0.0.1", alias="MYSQL_HOST")
    mysql_port: int = Field(3306, alias="MYSQL_PORT")
    mysql_db: str = Field("creator_saas", alias="MYSQL_DB")

    database_url: str | None = Field(None, alias="DATABASE_URL")

    secret_key: str = Field("", alias="SECRET_KEY")
    # 可选：与 JWT 分离的字段加密盐；未设置时回退使用 secret_key
    field_encryption_secret: str = Field("", alias="FIELD_ENCRYPTION_SECRET")
    algorithm: str = Field("HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    # 游客调用 YouTube 相关公共功能时读取该组织的设置中心配置。
    guest_default_org_id: int | None = Field(None, alias="GUEST_DEFAULT_ORG_ID")
    # 智能视觉 CV（图像修补 Inpaint）：AccessKey + SecretKey
    volc_cv_access_key_id: str = Field("", alias="VOLC_CV_ACCESS_KEY_ID")
    volc_cv_secret_access_key: str = Field("", alias="VOLC_CV_SECRET_ACCESS_KEY")
    volc_cv_region: str = Field("cn-north-1", alias="VOLC_CV_REGION")
    volc_cv_host: str = Field("", alias="VOLC_CV_HOST")
    volc_cv_inpaint_req_key: str = Field("i2i_inpainting", alias="VOLC_CV_INPAINT_REQ_KEY")
    aliyun_access_key_id: str = Field("", alias="ALIYUN_ACCESS_KEY_ID")
    aliyun_access_key_secret: str = Field("", alias="ALIYUN_ACCESS_KEY_SECRET")
    aliyun_role_arn: str = Field("", alias="ALIYUN_ROLE_ARN")
    aliyun_region_id: str = Field("", alias="ALIYUN_REGION_ID")
    aliyun_oss_bucket_name: str = Field("", alias="ALIYUN_OSS_BUCKET_NAME")
    aliyun_oss_endpoint: str = Field("", alias="ALIYUN_OSS_ENDPOINT")
    # 对外访问时替换默认 OSS 域名（须与桶绑定 CDN/自定义域名一致）
    aliyun_custom_domain: str = Field("", alias="ALIYUN_CUSTOM_DOMAIN")
    # 多云存储：新上传默认走哪一家（ALIYUN / TENCENT，大小写不敏感）
    active_storage_provider: str = Field("TENCENT", alias="ACTIVE_STORAGE_PROVIDER")
    tencent_cos_secret_id: str = Field("", alias="TENCENT_COS_SECRET_ID")
    tencent_cos_secret_key: str = Field("", alias="TENCENT_COS_SECRET_KEY")
    tencent_cos_region: str = Field("", alias="TENCENT_COS_REGION")
    tencent_cos_bucket: str = Field("", alias="TENCENT_COS_BUCKET")
    tencent_custom_domain: str = Field("", alias="TENCENT_CUSTOM_DOMAIN")
    google_oauth_client_id: str = Field("", alias="GOOGLE_OAUTH_CLIENT_ID")
    google_oauth_client_secret: str = Field("", alias="GOOGLE_OAUTH_CLIENT_SECRET")
    google_oauth_redirect_uri: str = Field("", alias="GOOGLE_OAUTH_REDIRECT_URI")

    # SMTP 邮件服务配置
    smtp_host: str = Field("", alias="SMTP_HOST")
    smtp_port: int = Field(465, alias="SMTP_PORT")
    smtp_user: str = Field("", alias="SMTP_USER")
    smtp_password: str = Field("", alias="SMTP_PASSWORD")
    smtp_from_email: str = Field("", alias="SMTP_FROM_EMAIL")
    smtp_use_ssl: bool = Field(True, alias="SMTP_USE_SSL")

    # 前端站点地址（用于生成密码重置等链接）
    frontend_base_url: str = Field("http://localhost:5173", alias="FRONTEND_BASE_URL")

    # yt-dlp 下载代理（可选，如 http://127.0.0.1:7890）
    download_proxy: str = Field("", alias="DOWNLOAD_PROXY")

    # 频道缓存 TTL（小时），默认 24 小时
    channel_cache_ttl_hours: int = Field(24, alias="CHANNEL_CACHE_TTL_HOURS")

    # 日志级别：DEBUG 时记录请求/响应 body，INFO 只记录请求行
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    # 信任的反向代理层数：0 表示不信任任何代理头（直接使用 request.client.host），
    # >0 时从 X-Forwarded-For 右侧倒数第 N 个位置取客户端真实 IP
    trusted_proxy_count: int = Field(0, alias="TRUSTED_PROXY_COUNT")

    # 支持单个 URL、逗号分隔字符串，或 JSON 数组字符串
    backend_cors_origins: str = Field(
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
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

    @model_validator(mode="after")
    def _validate_secret_key(self) -> "Settings":
        """启动时强制校验 SECRET_KEY，防止空值或弱密钥导致 JWT 伪造和加密失效。"""
        if not self.secret_key or len(self.secret_key) < 32:
            raise ValueError(
                "SECRET_KEY 必须设置且至少 32 个字符。"
                "请在 .env 或环境变量中配置强随机密钥，例如: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
