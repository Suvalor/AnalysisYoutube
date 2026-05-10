"""自定义访问域名：格式校验与可达性探测（HEAD，失败时回退 GET）。"""

from __future__ import annotations

from urllib.parse import urlparse

import httpx


def normalize_custom_domain(raw: str) -> str:
    """
    校验并规范化自定义访问域名根地址。
    必须包含 http:// 或 https://，且含有效主机名；去掉末尾斜杠。
    """
    s = (raw or "").strip()
    if not s:
        return ""
    if not s.startswith(("http://", "https://")):
        raise ValueError("自定义访问域名必须以 http:// 或 https:// 开头，例如 https://cdn.example.com")
    parsed = urlparse(s)
    if not parsed.netloc:
        raise ValueError("自定义访问域名无效：缺少主机名")
    return s.rstrip("/")


def _format_probe_failure(exc: BaseException) -> str:
    """将网络异常转为用户可读说明（避免仅显示裸异常类型）。"""
    if isinstance(exc, httpx.ConnectTimeout):
        return (
            "连接超时：请检查网络或防火墙；若刚修改 DNS，生效可能需要数分钟。"
        )
    if isinstance(exc, httpx.ReadTimeout):
        return "读取超时：对端响应过慢，请稍后重试。"
    if isinstance(exc, httpx.ConnectError):
        return (
            "无法建立连接：域名可能尚未解析（DNS 未生效）、端口未开放，"
            "或自定义域名未在云控制台正确绑定到存储桶/CDN。请核对解析与回源配置。"
        )
    if isinstance(exc, httpx.HTTPError):
        return f"请求失败：{exc}"
    return str(exc)


async def probe_domain_reachable(base_url: str) -> tuple[bool, str]:
    """
    对「根 URL + /」发起 HEAD；若对方不支持 HEAD 则尝试 GET。
    认为「能连上且 HTTP 状态 < 500」为可达（含 403/404，便于仅允许对象路径的 CDN）。
    """
    root = base_url.strip().rstrip("/") + "/"
    timeout = httpx.Timeout(12.0, connect=8.0)
    cors_hint = (
        " 浏览器内直接访问对象 URL 时，请在 OSS/COS 或 CDN 控制台配置 CORS（与本次服务端探测无关）。"
    )
    head_err: str | None = None
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            r = await client.head(root)
            if r.status_code >= 500:
                return False, f"HEAD 返回服务端错误 HTTP {r.status_code}"
            return True, f"验证通过：HEAD 可达（HTTP {r.status_code}）。{cors_hint}"
        except httpx.HTTPError as exc:
            head_err = _format_probe_failure(exc)

        try:
            r = await client.get(root)
            if r.status_code >= 500:
                return False, f"GET 返回服务端错误 HTTP {r.status_code}"
            return True, f"验证通过：GET 可达（HTTP {r.status_code}），HEAD 可能被禁用。{cors_hint}"
        except httpx.HTTPError as get_exc:
            if head_err is not None:
                return False, f"HEAD 失败：{head_err}；GET 失败：{_format_probe_failure(get_exc)}"
            return False, _format_probe_failure(get_exc)


async def validate_custom_domain_for_save(url: str) -> None:
    """保存前校验：非空则格式 + 可达性；失败抛 ValueError。"""
    norm = normalize_custom_domain(url)
    if not norm:
        return
    ok, msg = await probe_domain_reachable(norm)
    if not ok:
        raise ValueError(msg)
