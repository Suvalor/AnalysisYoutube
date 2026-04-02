"""集成配置「测试连接」：YouTube Data API、阿里云 OSS、腾讯云 COS。"""

from __future__ import annotations

import httpx
import oss2

from app.services.config_manager import ResolvedIntegrationConfig


def _format_tencent_cos_test_error(exc: BaseException) -> str:
    """将 COS SDK 异常转为可读说明（空错误体时 SDK 会把响应头当 message，直接 str 会像乱码字典）。"""
    try:
        from qcloud_cos.cos_exception import CosClientError, CosServiceError
    except ImportError:
        return str(exc)

    if isinstance(exc, CosClientError):
        return f"客户端或网络错误：{exc}"

    if isinstance(exc, CosServiceError):
        status = exc.get_status_code()
        digest = exc.get_digest_msg()
        # 服务端返回了 XML/JSON 错误体且已被 SDK 解析
        if isinstance(digest, dict) and "code" in digest:
            msg = digest.get("message") or ""
            rid = digest.get("requestid") or ""
            extra = f"（RequestId: {rid}）" if rid else ""
            return f"COS 接口错误 HTTP {status}：{digest.get('code')} — {msg}{extra}"
        # 空 body 时 SDK 把 headers 塞进 digest，用户会看到一整段 Header 字典
        req_id = ""
        if hasattr(digest, "get"):
            req_id = (
                digest.get("x-cos-request-id")
                or digest.get("X-Cos-Request-Id")
                or ""
            )
        rid_txt = f"x-cos-request-id={req_id}。" if req_id else ""
        return (
            f"腾讯云 COS 拒绝访问（HTTP {status}）。"
            + (f" {rid_txt} " if rid_txt else "")
            + "请核对：Region 与存储桶实际地域一致；桶名为「名称-APPID」完整格式；"
            "SecretId/SecretKey 正确且账号对该桶有权限（如 HeadBucket/List）。"
        )

    return str(exc)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
# 固定公开频道 ID，仅用于校验 key 是否有效
_YT_SMOKE_CHANNEL_ID = "UC_x5XG1OV2P6uZZ5FSM9Ttw"


async def test_youtube_api_key(api_key: str) -> tuple[bool, str]:
    key = (api_key or "").strip()
    if not key:
        return False, "API Key 为空"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{YOUTUBE_API_BASE}/channels",
                params={"part": "id", "id": _YT_SMOKE_CHANNEL_ID, "key": key},
            )
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
        data = r.json()
        if not data.get("items"):
            return False, "响应中无频道数据，请检查 Key 权限"
        return True, "YouTube Data API 调用成功"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def test_aliyun_oss(cfg: ResolvedIntegrationConfig) -> tuple[bool, str]:
    required = [
        cfg.aliyun_access_key_id,
        cfg.aliyun_access_key_secret,
        cfg.aliyun_oss_bucket_name,
        cfg.aliyun_oss_endpoint,
    ]
    if not all(required):
        return False, "阿里云 OSS 配置不完整"
    try:
        auth = oss2.Auth(cfg.aliyun_access_key_id, cfg.aliyun_access_key_secret)
        bucket = oss2.Bucket(
            auth,
            f"https://{cfg.aliyun_oss_endpoint}",
            cfg.aliyun_oss_bucket_name,
        )
        list(bucket.object_iterator(max_keys=1))
        return True, "阿里云 OSS 连接成功（已列举对象）"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def test_tencent_cos(cfg: ResolvedIntegrationConfig) -> tuple[bool, str]:
    required = [
        cfg.tencent_cos_secret_id,
        cfg.tencent_cos_secret_key,
        cfg.tencent_cos_region,
        cfg.tencent_cos_bucket,
    ]
    if not all(str(x).strip() for x in required):
        return False, "腾讯云 COS 配置不完整"
    try:
        from qcloud_cos import CosConfig, CosS3Client

        c = CosConfig(
            Region=cfg.tencent_cos_region,
            SecretId=cfg.tencent_cos_secret_id,
            SecretKey=cfg.tencent_cos_secret_key,
            Scheme="https",
        )
        client = CosS3Client(c)
        client.head_bucket(Bucket=cfg.tencent_cos_bucket)
        return True, "腾讯云 COS HeadBucket 成功"
    except Exception as exc:  # noqa: BLE001
        return False, _format_tencent_cos_test_error(exc)


def test_active_storage(cfg: ResolvedIntegrationConfig) -> tuple[bool, str]:
    """按当前合并配置中的 active_storage_provider 测试写入侧后端。"""
    from app.services.object_storage import normalize_storage_provider

    p = normalize_storage_provider(cfg.active_storage_provider)
    if p == "tencent":
        return test_tencent_cos(cfg)
    return test_aliyun_oss(cfg)
