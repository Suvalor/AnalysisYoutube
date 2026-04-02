"""组织级集成配置：云存储、YouTube、火山等；同组织成员共享 org_settings。"""

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
    IntegrationTestResult,
    ValidateStorageCustomDomainRequest,
)
from app.services.config_manager import (
    INTEGRATION_PAYLOAD_KEYS,
    SECRET_PAYLOAD_KEYS,
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


def _secret_display(merged_has: bool) -> str | None:
    return _MASK if merged_has else None


async def _to_read(session, org_id: int, stored: dict[str, str]) -> IntegrationSettingsRead:
    merged = merge_integration_config(stored)
    org = await session.get(Organization, org_id)
    org_name = org.name if org else ""
    return IntegrationSettingsRead(
        org_id=org_id,
        org_name=org_name,
        active_storage_provider=merged.active_storage_provider,
        aliyun_access_key_id=merged.aliyun_access_key_id,
        aliyun_role_arn=merged.aliyun_role_arn,
        aliyun_region_id=merged.aliyun_region_id,
        aliyun_oss_bucket_name=merged.aliyun_oss_bucket_name,
        aliyun_oss_endpoint=merged.aliyun_oss_endpoint,
        aliyun_custom_domain=merged.aliyun_custom_domain,
        tencent_cos_secret_id=merged.tencent_cos_secret_id,
        tencent_cos_region=merged.tencent_cos_region,
        tencent_cos_bucket=merged.tencent_cos_bucket,
        tencent_custom_domain=merged.tencent_custom_domain,
        volcengine_endpoint_id=merged.volcengine_endpoint_id,
        volcengine_base_url=merged.volcengine_base_url,
        volcengine_model_gemini=merged.volcengine_model_gemini,
        has_youtube_api_key=bool(merged.youtube_api_key),
        has_aliyun_access_key_secret=bool(merged.aliyun_access_key_secret),
        has_tencent_cos_secret_key=bool(merged.tencent_cos_secret_key),
        has_volcengine_api_key=bool(merged.volcengine_api_key),
        youtube_api_key_display=_secret_display(bool(merged.youtube_api_key)),
        aliyun_access_key_secret_display=_secret_display(bool(merged.aliyun_access_key_secret)),
        tencent_cos_secret_key_display=_secret_display(bool(merged.tencent_cos_secret_key)),
        volcengine_api_key_display=_secret_display(bool(merged.volcengine_api_key)),
    )


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
    response_model=IntegrationTestResult,
    summary="测试 YouTube Data API Key（合并后的有效 Key）",
)
async def test_youtube_integration(db: DBSessionDep, current_user: CurrentUserDep) -> IntegrationTestResult:
    org_id = _require_org_id(current_user)
    cfg = await resolve_integration_config(db, org_id=org_id)
    ok, msg = await test_youtube_api_key(cfg.youtube_api_key)
    return IntegrationTestResult(ok=ok, message=msg)


@router.post(
    "/me/integration-settings/test-storage",
    response_model=IntegrationTestResult,
    summary="测试当前默认云存储（按 ACTIVE_STORAGE_PROVIDER 选阿里云或腾讯云）",
)
async def test_storage_integration(db: DBSessionDep, current_user: CurrentUserDep) -> IntegrationTestResult:
    org_id = _require_org_id(current_user)
    cfg = await resolve_integration_config(db, org_id=org_id)
    ok, msg = test_active_storage(cfg)
    return IntegrationTestResult(ok=ok, message=msg)


@router.post(
    "/me/integration-settings/validate-storage-custom-domain",
    response_model=IntegrationTestResult,
    summary="校验云存储自定义访问域名（格式 + HEAD/GET 可达性）",
)
async def validate_storage_custom_domain(
    body: ValidateStorageCustomDomainRequest,
    current_user: CurrentUserDep,
) -> IntegrationTestResult:
    _require_org_id(current_user)
    try:
        norm = normalize_custom_domain(body.domain)
    except ValueError as exc:
        return IntegrationTestResult(ok=False, message=str(exc))
    if not norm:
        return IntegrationTestResult(ok=False, message="域名为空")
    ok, msg = await probe_domain_reachable(norm)
    label = "阿里云 OSS" if body.platform == "aliyun" else "腾讯云 COS"
    return IntegrationTestResult(ok=ok, message=f"【{label}】{msg}")
