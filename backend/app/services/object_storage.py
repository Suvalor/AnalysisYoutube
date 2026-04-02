"""
多云对象存储：写入侧由合并配置中的 active_storage_provider 决定；读取侧按库内 storage_platform 选择 SDK 生成链接。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit, urlparse, urlunsplit
from uuid import uuid4

import oss2
from fastapi import HTTPException, status

from app.services.config_manager import ResolvedIntegrationConfig

PLATFORM_ALIYUN = "aliyun"
PLATFORM_TENCENT = "tencent"


def _encoded_object_path(object_key: str) -> str:
    key = (object_key or "").strip().lstrip("/")
    if not key:
        return ""
    return "/".join(quote(seg, safe="") for seg in key.split("/"))


def rewrite_signed_url_host(signed_url: str, custom_base: str) -> str:
    """
    保留路径、查询串与 fragment，仅将 scheme/host 替换为自定义访问域名。
    签名参数仍在 query 中，适用于 CDN CNAME 到桶且 OSS/COS 校验路径与 query 的场景。
    """
    base = (custom_base or "").strip().rstrip("/")
    if not base:
        return signed_url
    if not base.startswith(("http://", "https://")):
        base = "https://" + base.lstrip("/")
    sp = urlsplit(signed_url)
    bp = urlsplit(base)
    if not bp.scheme or not bp.netloc:
        return signed_url
    return urlunsplit((bp.scheme, bp.netloc, sp.path, sp.query, sp.fragment))


def build_material_object_key(file_type: str, original_name: str) -> str:
    """与 upload_local_file 一致的对象键规则，供预签名 PUT 与后端上传共用。"""
    ext = Path(original_name).suffix
    return f"materials/{file_type}/{datetime.utcnow():%Y/%m/%d}/{uuid4().hex}{ext}"


def public_url_with_custom_base(custom_base: str, object_key: str) -> str:
    """{custom_base}/{编码后的 object_key}"""
    base = (custom_base or "").strip().rstrip("/")
    enc = _encoded_object_path(object_key)
    if not base:
        return ""
    return f"{base}/{enc}" if enc else base


@dataclass(frozen=True)
class StoredObject:
    """一次上传的落库信息：公网可访问 URL（若桶私有则仅作记录）、对象键、平台标识。"""

    public_url: str
    object_key: str
    storage_platform: str


def normalize_storage_provider(raw: str | None) -> str:
    """将配置或入参规范为 aliyun / tencent。"""
    n = (raw or "").strip().upper()
    if n in ("ALIYUN", "OSS", "ALIYUN_OSS"):
        return PLATFORM_ALIYUN
    if n in ("TENCENT", "COS", "TENCENT_COS", "COS_TENCENT", "QCLOUD"):
        return PLATFORM_TENCENT
    return PLATFORM_TENCENT


class ObjectStorageBackend(ABC):
    """存储后端策略接口。"""

    platform: str

    @abstractmethod
    def upload_local_file(self, local_path: str, file_type: str, original_name: str) -> StoredObject:
        """上传本地文件，返回公网 URL、对象键与平台。"""

    @abstractmethod
    def presigned_get_url(self, object_key: str, expires_seconds: int) -> str:
        """生成临时下载/预览 URL。"""

    @abstractmethod
    def presigned_put_url(
        self,
        object_key: str,
        expires_seconds: int,
        content_type: str | None,
    ) -> tuple[str, dict[str, str]]:
        """
        生成浏览器直传 PUT 用预签名 URL。
        返回 (upload_url, required_headers)；upload_url 保持云厂商原始 Host 以保证签名校验。
        """

    @abstractmethod
    def material_record_url(self, object_key: str) -> str:
        """落库用 file_url（优先自定义访问域名）。"""


class AliyunOSSBackend(ObjectStorageBackend):
    platform = PLATFORM_ALIYUN

    def __init__(self, cfg: ResolvedIntegrationConfig) -> None:
        self._cfg = cfg

    def _aliyun_custom_root(self) -> str:
        """仅阿里云配置：自定义访问域名根，与腾讯云字段严格隔离。"""
        return (self._cfg.aliyun_custom_domain or "").strip().rstrip("/")

    def _bucket(self) -> oss2.Bucket:
        required = [
            self._cfg.aliyun_access_key_id,
            self._cfg.aliyun_access_key_secret,
            self._cfg.aliyun_oss_bucket_name,
            self._cfg.aliyun_oss_endpoint,
        ]
        if not all(required):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="阿里云 OSS 配置不完整",
            )
        auth = oss2.Auth(self._cfg.aliyun_access_key_id, self._cfg.aliyun_access_key_secret)
        return oss2.Bucket(
            auth,
            f"https://{self._cfg.aliyun_oss_endpoint}",
            self._cfg.aliyun_oss_bucket_name,
        )

    def _public_url(self, object_key: str) -> str:
        custom = self._aliyun_custom_root()
        if custom:
            return public_url_with_custom_base(custom, object_key)
        endpoint = self._cfg.aliyun_oss_endpoint
        bucket = self._cfg.aliyun_oss_bucket_name
        enc = _encoded_object_path(object_key)
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return f"{endpoint.rstrip('/')}/{enc}"
        return f"https://{bucket}.{endpoint}/{enc}"

    def upload_local_file(self, local_path: str, file_type: str, original_name: str) -> StoredObject:
        bucket = self._bucket()
        object_key = build_material_object_key(file_type, original_name)
        try:
            bucket.put_object_from_file(object_key, local_path)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"上传阿里云 OSS 失败: {exc}",
            ) from exc
        return StoredObject(
            public_url=self._public_url(object_key),
            object_key=object_key,
            storage_platform=self.platform,
        )

    def presigned_get_url(self, object_key: str, expires_seconds: int) -> str:
        bucket = self._bucket()
        try:
            raw = bucket.sign_url("GET", object_key, expires_seconds, slash_safe=True)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"生成阿里云 OSS 签名 URL 失败: {exc}",
            ) from exc
        custom = self._aliyun_custom_root()
        if custom:
            return rewrite_signed_url_host(raw, custom)
        return raw

    def presigned_put_url(
        self,
        object_key: str,
        expires_seconds: int,
        content_type: str | None,
    ) -> tuple[str, dict[str, str]]:
        bucket = self._bucket()
        ct = (content_type or "").strip() or "application/octet-stream"
        headers: dict[str, str] = {"Content-Type": ct}
        try:
            raw = bucket.sign_url("PUT", object_key, int(expires_seconds), headers=headers, slash_safe=True)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"生成阿里云 OSS PUT 预签名 URL 失败: {exc}",
            ) from exc
        return raw, headers

    def material_record_url(self, object_key: str) -> str:
        return self._public_url(object_key)


class TencentCOSBackend(ObjectStorageBackend):
    platform = PLATFORM_TENCENT

    def __init__(self, cfg: ResolvedIntegrationConfig) -> None:
        from qcloud_cos import CosConfig, CosS3Client

        self._cfg = cfg
        required = [
            cfg.tencent_cos_secret_id,
            cfg.tencent_cos_secret_key,
            cfg.tencent_cos_region,
            cfg.tencent_cos_bucket,
        ]
        if not all(str(x).strip() for x in required):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="腾讯云 COS 配置不完整",
            )
        cos_cfg = CosConfig(
            Region=cfg.tencent_cos_region,
            SecretId=cfg.tencent_cos_secret_id,
            SecretKey=cfg.tencent_cos_secret_key,
            Scheme="https",
        )
        self._client = CosS3Client(cos_cfg)
        self._bucket = cfg.tencent_cos_bucket
        self._region = cfg.tencent_cos_region

    def _tencent_custom_root(self) -> str:
        """仅腾讯云配置：自定义访问域名根，与阿里云字段严格隔离。"""
        return (self._cfg.tencent_custom_domain or "").strip().rstrip("/")

    def _public_url(self, object_key: str) -> str:
        custom = self._tencent_custom_root()
        if custom:
            return public_url_with_custom_base(custom, object_key)
        enc = _encoded_object_path(object_key)
        return f"https://{self._bucket}.cos.{self._region}.myqcloud.com/{enc}"

    def upload_local_file(self, local_path: str, file_type: str, original_name: str) -> StoredObject:
        object_key = build_material_object_key(file_type, original_name)
        try:
            self._client.upload_file(Bucket=self._bucket, LocalFilePath=local_path, Key=object_key)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"上传腾讯云 COS 失败: {exc}",
            ) from exc
        return StoredObject(
            public_url=self._public_url(object_key),
            object_key=object_key,
            storage_platform=self.platform,
        )

    def presigned_get_url(self, object_key: str, expires_seconds: int) -> str:
        try:
            raw = self._client.get_presigned_download_url(
                Bucket=self._bucket,
                Key=object_key,
                Expired=int(expires_seconds),
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"生成腾讯云 COS 签名 URL 失败: {exc}",
            ) from exc
        custom = self._tencent_custom_root()
        if custom:
            return rewrite_signed_url_host(raw, custom)
        return raw

    def presigned_put_url(
        self,
        object_key: str,
        expires_seconds: int,
        content_type: str | None,
    ) -> tuple[str, dict[str, str]]:
        ct = (content_type or "").strip() or "application/octet-stream"
        hdrs: dict[str, str] = {"Content-Type": ct}
        try:
            raw = self._client.get_presigned_url(
                Method="PUT",
                Bucket=self._bucket,
                Key=object_key,
                Expired=int(expires_seconds),
                Headers=hdrs,
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"生成腾讯云 COS PUT 预签名 URL 失败: {exc}",
            ) from exc
        if not isinstance(raw, str):
            raw = str(raw)
        return raw, hdrs

    def material_record_url(self, object_key: str) -> str:
        return self._public_url(object_key)


def get_write_backend(cfg: ResolvedIntegrationConfig) -> ObjectStorageBackend:
    """新文件上传使用的后端，由合并配置中的 active_storage_provider 决定。"""
    p = normalize_storage_provider(cfg.active_storage_provider)
    if p == PLATFORM_TENCENT:
        return TencentCOSBackend(cfg)
    return AliyunOSSBackend(cfg)


def get_backend_for_platform(storage_platform: str | None, cfg: ResolvedIntegrationConfig) -> ObjectStorageBackend:
    """
    按库内记录的 storage_platform 选择后端，用于生成访问链接。
    严禁使用全局开关代替本条。
    """
    p = (storage_platform or "").strip().lower()
    if not p:
        p = PLATFORM_ALIYUN
    if p == PLATFORM_TENCENT:
        return TencentCOSBackend(cfg)
    if p == PLATFORM_ALIYUN:
        return AliyunOSSBackend(cfg)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"不支持的 storage_platform: {storage_platform!r}",
    )


def infer_object_key_from_file_url(
    file_url: str,
    storage_platform: str | None,
    cfg: ResolvedIntegrationConfig,
) -> str | None:
    """
    旧数据仅有 file_url、无 storage_object_key 时，尝试从 URL 反推对象键（仅信任 materials/ 前缀）。
    用于私有桶下仍能生成签名 URL（自定义域名由 presign 后 rewrite 处理）。
    """
    raw = (file_url or "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    path = unquote((parsed.path or "").lstrip("/"))
    if not path.startswith("materials/"):
        return None
    plat = (storage_platform or PLATFORM_ALIYUN).strip().lower()
    host = (parsed.netloc or "").lower()

    if plat == PLATFORM_ALIYUN:
        custom = (cfg.aliyun_custom_domain or "").strip().rstrip("/")
        if custom:
            cu = urlparse(custom if custom.startswith("http") else f"https://{custom}")
            if host == (cu.netloc or "").lower() or raw.startswith(custom):
                return path
        bucket = (cfg.aliyun_oss_bucket_name or "").strip().lower()
        ep = (cfg.aliyun_oss_endpoint or "").strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
        if bucket and ep and host == f"{bucket}.{ep}":
            return path

    if plat == PLATFORM_TENCENT:
        custom = (cfg.tencent_custom_domain or "").strip().rstrip("/")
        if custom:
            cu = urlparse(custom if custom.startswith("http") else f"https://{custom}")
            if host == (cu.netloc or "").lower() or raw.startswith(custom):
                return path
        bucket = (cfg.tencent_cos_bucket or "").strip().lower()
        region = (cfg.tencent_cos_region or "").strip().lower()
        if bucket and region:
            expected = f"{bucket}.cos.{region}.myqcloud.com"
            if host == expected:
                return path

    return None


def material_access_url(
    *,
    storage_platform: str | None,
    storage_object_key: str | None,
    file_url_fallback: str,
    expires_seconds: int,
    cfg: ResolvedIntegrationConfig,
) -> tuple[str, str]:
    """
    返回 (url, mode)。mode 为 presigned 或 public_fallback。
    无 object_key 时尝试从 file_url 推断键；仍失败则退回 file_url。
    """
    fb = (file_url_fallback or "").strip()
    key = (storage_object_key or "").strip()
    if not key:
        inferred = infer_object_key_from_file_url(fb, storage_platform, cfg)
        if inferred:
            key = inferred
    if key:
        try:
            backend = get_backend_for_platform(storage_platform, cfg)
            url = backend.presigned_get_url(key, expires_seconds)
            return url, "presigned"
        except Exception:  # noqa: BLE001
            pass
    return fb, "public_fallback"
