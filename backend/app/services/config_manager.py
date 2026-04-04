"""
组织级集成配置与环境变量合并：org_settings（按 org_id）优先，缺项回退 Settings。
定时任务等场景显式传入 org_id 即可加载租户自定义 Key。
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.crud.org_settings import get_org_integration_payload_dict

INTEGRATION_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {
        "youtube_api_key",
        "active_storage_provider",
        "aliyun_access_key_id",
        "aliyun_access_key_secret",
        "aliyun_role_arn",
        "aliyun_region_id",
        "aliyun_oss_bucket_name",
        "aliyun_oss_endpoint",
        "aliyun_custom_domain",
        "tencent_cos_secret_id",
        "tencent_cos_secret_key",
        "tencent_cos_region",
        "tencent_cos_bucket",
        "tencent_custom_domain",
        "volcengine_api_key",
        "volcengine_endpoint_id",
        "volcengine_base_url",
        "volcengine_model_gemini",
        # 去水印插件：组织级默认（可被 model_libraries 中 image_inpaint 条目覆盖密钥与 Base URL）
        "watermark_video_ai_max_frames",
        "watermark_inpaint_prompt",
        # 火山智能视觉 CV（图像修补），与 volcengine_api_key（方舟/LLM）分离
        "volc_cv_access_key_id",
        "volc_cv_secret_access_key",
        "volc_cv_region",
        "volc_cv_host",
        "volc_cv_inpaint_req_key",
    }
)

SECRET_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {
        "youtube_api_key",
        "aliyun_access_key_secret",
        "tencent_cos_secret_key",
        "volcengine_api_key",
        "volc_cv_secret_access_key",
    }
)

# 前端或误操作传入的脱敏占位，禁止写入数据库
SECRET_PLACEHOLDER_VALUES: frozenset[str] = frozenset(
    {
        "********",
        "*******",
        "****",
        "***",
        "••••••••",
    }
)


def is_secret_placeholder(value: str | None) -> bool:
    s = (value or "").strip()
    if not s:
        return False
    if s in SECRET_PLACEHOLDER_VALUES:
        return True
    if all(c in "*•·." for c in s) and len(s) >= 4:
        return True
    return False


def _pick_str(db: dict[str, str], key: str, fallback: str) -> str:
    v = (db.get(key) or "").strip()
    if v:
        return v
    return (fallback or "").strip()


DEFAULT_WATERMARK_INPAINT_PROMPT = (
    "Remove overlaid text or watermark and naturally inpaint the background. "
    "Keep areas outside the mask unchanged in style."
)


def _pick_int_clamped(db: dict[str, str], key: str, default: int, *, lo: int, hi: int) -> int:
    raw = (db.get(key) or "").strip()
    if not raw:
        return default
    try:
        return max(lo, min(hi, int(raw)))
    except ValueError:
        return default


@dataclass
class ResolvedIntegrationConfig:
    """合并后的有效配置，供对象存储、YouTube API、火山兼容调用等使用。"""

    youtube_api_key: str
    active_storage_provider: str
    aliyun_access_key_id: str
    aliyun_access_key_secret: str
    aliyun_role_arn: str
    aliyun_region_id: str
    aliyun_oss_bucket_name: str
    aliyun_oss_endpoint: str
    aliyun_custom_domain: str
    tencent_cos_secret_id: str
    tencent_cos_secret_key: str
    tencent_cos_region: str
    tencent_cos_bucket: str
    tencent_custom_domain: str
    volcengine_api_key: str
    volcengine_endpoint_id: str
    volcengine_base_url: str
    volcengine_model_gemini: str
    volc_cv_access_key_id: str
    volc_cv_secret_access_key: str
    volc_cv_region: str
    volc_cv_host: str
    volc_cv_inpaint_req_key: str
    watermark_video_ai_max_frames: int
    watermark_inpaint_prompt: str


def merge_integration_config(db_payload: dict[str, str] | None, s: Settings | None = None) -> ResolvedIntegrationConfig:
    d = db_payload or {}
    base = s or get_settings()
    return ResolvedIntegrationConfig(
        youtube_api_key=_pick_str(d, "youtube_api_key", base.youtube_api_key),
        active_storage_provider=_pick_str(d, "active_storage_provider", base.active_storage_provider),
        aliyun_access_key_id=_pick_str(d, "aliyun_access_key_id", base.aliyun_access_key_id),
        aliyun_access_key_secret=_pick_str(d, "aliyun_access_key_secret", base.aliyun_access_key_secret),
        aliyun_role_arn=_pick_str(d, "aliyun_role_arn", base.aliyun_role_arn),
        aliyun_region_id=_pick_str(d, "aliyun_region_id", base.aliyun_region_id),
        aliyun_oss_bucket_name=_pick_str(d, "aliyun_oss_bucket_name", base.aliyun_oss_bucket_name),
        aliyun_oss_endpoint=_pick_str(d, "aliyun_oss_endpoint", base.aliyun_oss_endpoint),
        aliyun_custom_domain=_pick_str(d, "aliyun_custom_domain", base.aliyun_custom_domain),
        tencent_cos_secret_id=_pick_str(d, "tencent_cos_secret_id", base.tencent_cos_secret_id),
        tencent_cos_secret_key=_pick_str(d, "tencent_cos_secret_key", base.tencent_cos_secret_key),
        tencent_cos_region=_pick_str(d, "tencent_cos_region", base.tencent_cos_region),
        tencent_cos_bucket=_pick_str(d, "tencent_cos_bucket", base.tencent_cos_bucket),
        tencent_custom_domain=_pick_str(d, "tencent_custom_domain", base.tencent_custom_domain),
        volcengine_api_key=_pick_str(d, "volcengine_api_key", base.volcengine_api_key),
        volcengine_endpoint_id=_pick_str(d, "volcengine_endpoint_id", base.volcengine_endpoint_id),
        volcengine_base_url=_pick_str(d, "volcengine_base_url", base.volcengine_base_url),
        volcengine_model_gemini=_pick_str(d, "volcengine_model_gemini", base.volcengine_model_gemini),
        volc_cv_access_key_id=_pick_str(d, "volc_cv_access_key_id", base.volc_cv_access_key_id),
        volc_cv_secret_access_key=_pick_str(d, "volc_cv_secret_access_key", base.volc_cv_secret_access_key),
        volc_cv_region=_pick_str(d, "volc_cv_region", base.volc_cv_region),
        volc_cv_host=_pick_str(d, "volc_cv_host", base.volc_cv_host),
        volc_cv_inpaint_req_key=_pick_str(d, "volc_cv_inpaint_req_key", base.volc_cv_inpaint_req_key),
        watermark_video_ai_max_frames=_pick_int_clamped(
            d, "watermark_video_ai_max_frames", 180, lo=1, hi=10000
        ),
        watermark_inpaint_prompt=_pick_str(d, "watermark_inpaint_prompt", DEFAULT_WATERMARK_INPAINT_PROMPT),
    )


async def resolve_integration_config(
    session: AsyncSession | None,
    *,
    org_id: int | None = None,
) -> ResolvedIntegrationConfig:
    """
    解析有效集成配置。
    org_id 为空或 session 为空时，仅使用环境变量 / Settings。
    """
    db_payload: dict[str, str] = {}
    if session is not None and org_id is not None:
        db_payload = await get_org_integration_payload_dict(session, org_id)
    return merge_integration_config(db_payload)


def resolve_model_alias_for_volcengine(model_alias: str, cfg: ResolvedIntegrationConfig) -> str:
    model_alias = (model_alias or "").strip()
    if not model_alias:
        return cfg.volcengine_endpoint_id
    alias_map = {
        "gemini-1.5-pro": cfg.volcengine_model_gemini or cfg.volcengine_endpoint_id,
        "claude-3-5-sonnet": cfg.volcengine_endpoint_id,
    }
    return alias_map.get(model_alias, model_alias)


def looks_like_volcengine_ark_base_url(api_base_url: str) -> bool:
    """火山引擎方舟 OpenAI 兼容接口：chat.completions 的 model 须为推理接入点 ID（ep- 开头）。"""
    u = (api_base_url or "").strip().lower()
    if not u:
        return False
    return "volces.com" in u or "volcengineapi.com" in u


