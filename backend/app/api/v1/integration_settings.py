"""组织级集成配置：云存储、YouTube、CV 等；同组织成员共享 org_settings。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserDep, DBSessionDep
from app.crud.org_settings import (
    delete_org_integration_settings,
    get_org_integration_payload_dict,
    upsert_org_integration_payload,
)
from app.models.organization import Organization
from app.schemas.integration_settings import (
    IntegrationSettingsRead,
    IntegrationSettingsUpdate,
)
from app.services.config_manager import (
    INTEGRATION_PAYLOAD_KEYS,
    SECRET_PAYLOAD_KEYS,
    SEMI_SECRET_PAYLOAD_KEYS,
    is_secret_placeholder,
    merge_integration_config,
    resolve_integration_config,
)
from app.services.custom_domain_validation import (
    normalize_custom_domain,
    probe_domain_reachable,
    validate_custom_domain_for_save,
)
from app.services.integration_test_service import test_active_storage, test_youtube_api_key

router = APIRouter()

_MASK = "********"


def _secret_display(merged_has: bool) -> str:
    return _MASK if merged_has else ""


def _semi_secret_display(value: str | None) -> str:
    """对半敏感字段脱敏：保留后4位，前面用 **** 替代。"""
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return "****" + value[-4:]


async def _to_read(session, org_id: int, stored: dict[str, str]) -> IntegrationSettingsRead:
    merged = merge_integration_config(stored)
    org = await session.get(Organization, org_id)
    org_name = org.name if org else ""

    # 构建字段值映射，对敏感字段脱敏
    raw: dict[str, str | int] = {
        "youtube_api_key": merged.youtube_api_key,
        "active_storage_provider": merged.active_storage_provider,
        "aliyun_access_key_id": merged.aliyun_access_key_id,
        "aliyun_access_key_secret": merged.aliyun_access_key_secret,
        "aliyun_role_arn": merged.aliyun_role_arn,
        "aliyun_region_id": merged.aliyun_region_id,
        "aliyun_oss_bucket_name": merged.aliyun_oss_bucket_name,
        "aliyun_oss_endpoint": merged.aliyun_oss_endpoint,
        "aliyun_custom_domain": merged.aliyun_custom_domain,
        "tencent_cos_secret_id": merged.tencent_cos_secret_id,
        "tencent_cos_secret_key": merged.tencent_cos_secret_key,
        "tencent_cos_region": merged.tencent_cos_region,
        "tencent_cos_bucket": merged.tencent_cos_bucket,
        "tencent_custom_domain": merged.tencent_custom_domain,
        "volc_cv_access_key_id": merged.volc_cv_access_key_id,
        "volc_cv_secret_access_key": merged.volc_cv_secret_access_key,
        "volc_cv_region": merged.volc_cv_region,
        "volc_cv_host": merged.volc_cv_host,
        "volc_cv_inpaint_req_key": merged.volc_cv_inpaint_req_key,
        "watermark_video_ai_max_frames": merged.watermark_video_ai_max_frames,
        "watermark_inpaint_prompt": merged.watermark_inpaint_prompt,
        "google_oauth_client_id": merged.google_oauth_client_id,
        "google_oauth_client_secret": merged.google_oauth_client_secret,
        "google_oauth_redirect_uri": merged.google_oauth_redirect_uri,
    }

    for key in SECRET_PAYLOAD_KEYS:
        if key in raw:
            raw[key] = _secret_display(bool(raw[key]))

    for key in SEMI_SECRET_PAYLOAD_KEYS:
        if key in raw:
            raw[key] = _semi_secret_display(str(raw[key]))

    raw["has_google_oauth_client_secret"] = bool(merged.google_oauth_client_secret)

    return IntegrationSettingsRead(**raw)


def _require_org_id(current_user) -> int:
    oid = getattr(current_user, "org_id", None)
    if oid is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前账号未关联组织，无法读写集成配置",
        )
    return int(oid)


@router.get("/me/integration-settings", response_model=IntegrationSettingsRead, summary="获取组织集成配置（脱敏）")
async def get_integration_settings(db: DBSessionDep, current_user: CurrentUserDep) -> IntegrationSettingsRead:
    org_id = _require_org_id(current_user)
    stored = await get_org_integration_payload_dict(db, org_id)
    return await _to_read(db, org_id, stored)


@router.put("/me/integration-settings", response_model=IntegrationSettingsRead, summary="增量更新组织集成配置")
async def put_integration_settings(
    body: IntegrationSettingsUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> IntegrationSettingsRead:
    org_id = _require_org_id(current_user)
    inner = await get_org_integration_payload_dict(db, org_id)
    incoming = body.model_dump(exclude_unset=True)

    for key, val in incoming.items():
        if key not in INTEGRATION_PAYLOAD_KEYS:
            continue
        if val is None:
            inner.pop(key, None)
            continue
        if key in SECRET_PAYLOAD_KEYS:
            s = str(val).strip()
            if not s or is_secret_placeholder(s):
                continue
            inner[key] = s
            continue
        s = str(val).strip()
        if s:
            inner[key] = s
        else:
            inner.pop(key, None)

    try:
        if "aliyun_custom_domain" in incoming:
            v = (inner.get("aliyun_custom_domain") or "").strip()
            if v:
                await validate_custom_domain_for_save(v)
        if "tencent_custom_domain" in incoming:
            v = (inner.get("tencent_custom_domain") or "").strip()
            if v:
                await validate_custom_domain_for_save(v)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await upsert_org_integration_payload(db, org_id, inner)
    return await _to_read(db, org_id, inner)


@router.delete("/me/integration-settings", summary="清除本组织库内集成覆盖（回退环境变量）")
async def delete_org_integration_settings_route(db: DBSessionDep, current_user: CurrentUserDep) -> dict[str, str]:
    org_id = _require_org_id(current_user)
    await delete_org_integration_settings(db, org_id)
    return {"message": "已清除本组织在库内的集成覆盖，现使用环境变量默认值"}


@router.post(
    "/me/integration-settings/test-youtube",
    summary="测试 YouTube Data API Key",
)
async def test_youtube_integration(db: DBSessionDep, current_user: CurrentUserDep) -> dict[str, str]:
    org_id = _require_org_id(current_user)
    cfg = await resolve_integration_config(db, org_id=org_id)
    ok, msg = await test_youtube_api_key(cfg.youtube_api_key)
    return {"ok": str(ok), "message": msg}


@router.post(
    "/me/integration-settings/test-storage",
    summary="测试当前默认云存储",
)
async def test_storage_integration(db: DBSessionDep, current_user: CurrentUserDep) -> dict[str, str]:
    org_id = _require_org_id(current_user)
    cfg = await resolve_integration_config(db, org_id=org_id)
    ok, msg = test_active_storage(cfg)
    return {"ok": str(ok), "message": msg}


@router.post(
    "/me/integration-settings/validate-storage-custom-domain",
    summary="校验云存储自定义访问域名",
)
async def validate_storage_custom_domain(
    body: dict[str, str],
    current_user: CurrentUserDep,
) -> dict[str, str]:
    _require_org_id(current_user)
    domain = body.get("domain", "").strip()
    platform = body.get("platform", "aliyun")
    try:
        norm = normalize_custom_domain(domain)
    except ValueError as exc:
        return {"ok": "false", "message": str(exc)}
    if not norm:
        return {"ok": "false", "message": "域名为空"}
    ok, msg = await probe_domain_reachable(norm)
    label = "阿里云 OSS" if platform == "aliyun" else "腾讯云 COS"
    return {"ok": str(ok), "message": f"【{label}】{msg}"}