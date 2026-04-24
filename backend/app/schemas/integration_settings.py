"""组织级集成配置 API：读为合并后视图；写为增量合并（exclude_unset）。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.ssrf_guard import validate_url_against_ssrf


class IntegrationSettingsRead(BaseModel):
    """非密钥字段为合并后的有效值；密钥以 has_* 与 *_display 提示，勿将 display 回传。"""

    model_config = ConfigDict(from_attributes=True)

    org_id: int = Field(..., description="当前配置归属组织")
    org_name: str = Field("", description="组织名称")

    active_storage_provider: str = Field("", description="默认上传存储：ALIYUN / TENCENT 等")
    aliyun_access_key_id: str = ""
    aliyun_role_arn: str = ""
    aliyun_region_id: str = ""
    aliyun_oss_bucket_name: str = ""
    aliyun_oss_endpoint: str = ""
    aliyun_custom_domain: str = Field("", description="对外访问用自有域名，如 https://cdn.example.com")
    tencent_cos_secret_id: str = ""
    tencent_cos_region: str = ""
    tencent_cos_bucket: str = ""
    tencent_custom_domain: str = Field("", description="COS 对外访问用自有域名")
    volcengine_endpoint_id: str = ""
    volcengine_base_url: str = ""
    volcengine_model_gemini: str = ""
    volc_cv_access_key_id: str = Field("", description="智能视觉 CV AccessKey（图像修补，与方舟 API Key 不同）")
    volc_cv_region: str = ""
    volc_cv_host: str = Field("", description="可选，自定义 API Host（不含 https://）")
    volc_cv_inpaint_req_key: str = Field("", description="Img2ImgInpainting 的 req_key，默认 i2i_inpainting")
    watermark_video_ai_max_frames: int = Field(180, description="视频 AI 去水印最大帧数阈值（预留配置）")
    watermark_inpaint_prompt: str = Field("", description="去水印 images.edit 提示词（组织默认）")

    has_youtube_api_key: bool = False
    has_aliyun_access_key_secret: bool = False
    has_tencent_cos_secret_key: bool = False
    has_volcengine_api_key: bool = False
    has_volc_cv_secret_access_key: bool = False

    youtube_api_key_display: str | None = Field(None, description="已配置时为 ********，勿作为新密钥提交")
    aliyun_access_key_secret_display: str | None = None
    tencent_cos_secret_key_display: str | None = None
    volcengine_api_key_display: str | None = None
    volc_cv_secret_access_key_display: str | None = None


class IntegrationSettingsUpdate(BaseModel):
    """增量更新：仅提交需要变更的字段（Pydantic exclude_unset）。密钥：非空且非占位符才写入；null 删除库内覆盖。"""

    model_config = ConfigDict(extra="ignore")

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
    volcengine_api_key: str | None = None
    volcengine_endpoint_id: str | None = None
    volcengine_base_url: str | None = None
    volcengine_model_gemini: str | None = None
    volc_cv_access_key_id: str | None = None
    volc_cv_secret_access_key: str | None = None
    volc_cv_region: str | None = None
    volc_cv_host: str | None = None
    volc_cv_inpaint_req_key: str | None = None
    watermark_video_ai_max_frames: int | None = Field(None, ge=1, le=10000)
    watermark_inpaint_prompt: str | None = None


class IntegrationTestResult(BaseModel):
    ok: bool
    message: str


class ValidateStorageCustomDomainRequest(BaseModel):
    """测试自定义访问域名是否格式正确且网络可达。"""

    platform: Literal["aliyun", "tencent"]
    domain: str = Field(..., min_length=1, description="完整 URL，须含 http/https")
