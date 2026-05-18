from __future__ import annotations

from pydantic import BaseModel, Field


class IntegrationSettingsRead(BaseModel):
    """前端读取集成配置时返回（密钥脱敏）。"""

    youtube_api_key: str = ""
    active_storage_provider: str = ""
    aliyun_access_key_id: str = ""
    aliyun_access_key_secret: str = ""
    aliyun_role_arn: str = ""
    aliyun_region_id: str = ""
    aliyun_oss_bucket_name: str = ""
    aliyun_oss_endpoint: str = ""
    aliyun_custom_domain: str = ""
    tencent_cos_secret_id: str = ""
    tencent_cos_secret_key: str = ""
    tencent_cos_region: str = ""
    tencent_cos_bucket: str = ""
    tencent_custom_domain: str = ""
    volc_cv_access_key_id: str = ""
    volc_cv_secret_access_key: str = ""
    volc_cv_region: str = ""
    volc_cv_host: str = ""
    volc_cv_inpaint_req_key: str = ""
    watermark_video_ai_max_frames: int = 180
    watermark_inpaint_prompt: str = ""
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_redirect_uri: str = ""
    has_google_oauth_client_secret: bool = False


class IntegrationSettingsUpdate(BaseModel):
    """前端更新集成配置时提交。"""

    youtube_api_key: str | None = None
    active_storage_provider: str | None = None
    aliyun_access_key_id: str | None = None
    aliyun_access_key_secret: str | None = None
    aliyun_role_arn: str | None = None
    aliyun_region_id: str | None = None
    aliyun_oss_bucket_name: str | None = None
    aliyun_oss_endpoint: str | None = None
    aliyun_custom_domain: str | None = None
    tencent_cos_secret_id: str | None = None
    tencent_cos_secret_key: str | None = None
    tencent_cos_region: str | None = None
    tencent_cos_bucket: str | None = None
    tencent_custom_domain: str | None = None
    volc_cv_access_key_id: str | None = None
    volc_cv_secret_access_key: str | None = None
    volc_cv_region: str | None = None
    volc_cv_host: str | None = None
    volc_cv_inpaint_req_key: str | None = None
    watermark_video_ai_max_frames: int | None = None
    watermark_inpaint_prompt: str | None = None
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    google_oauth_redirect_uri: str | None = None
