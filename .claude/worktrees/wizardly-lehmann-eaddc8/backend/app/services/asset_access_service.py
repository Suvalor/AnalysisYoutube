"""
列表/详情统一生成带签名的 access_url（Host 已由 object_storage 替换为自定义域名）。
"""

from __future__ import annotations

from app.models.library import AssetLibrary
from app.services.config_manager import ResolvedIntegrationConfig
from app.services.object_storage import material_access_url

# 列表与详情默认 1 小时；与需求「时效性如 1 小时」一致
LIST_ACCESS_URL_TTL_SECONDS = 3600


def library_row_access_url(
    row: AssetLibrary,
    cfg: ResolvedIntegrationConfig,
    expires_seconds: int = LIST_ACCESS_URL_TTL_SECONDS,
) -> str:
    """asset_libraries 一行 → 可访问 URL（有 object_key 时为签名 URL）。"""
    url, _ = material_access_url(
        storage_platform=row.storage_platform,
        storage_object_key=row.storage_object_key,
        file_url_fallback=row.file_url,
        expires_seconds=expires_seconds,
        cfg=cfg,
    )
    return url


def sop_file_access_url(
    *,
    storage_platform: str | None,
    storage_object_key: str | None,
    file_url: str | None,
    cfg: ResolvedIntegrationConfig,
    expires_seconds: int = LIST_ACCESS_URL_TTL_SECONDS,
) -> str | None:
    """SOP 资产/媒体：有 object_key 或 file_url 时生成访问链接。"""
    key = (storage_object_key or "").strip()
    fb = (file_url or "").strip()
    if not key and not fb:
        return None
    url, _ = material_access_url(
        storage_platform=storage_platform,
        storage_object_key=key or None,
        file_url_fallback=fb,
        expires_seconds=expires_seconds,
        cfg=cfg,
    )
    return url
