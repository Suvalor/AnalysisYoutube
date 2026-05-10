"""SSRF 防护：校验用户提交的 URL 是否指向私有 / 保留网络地址。"""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse


def validate_url_against_ssrf(url: str, *, allow_localhost: bool = False) -> str:
    """校验 URL 不指向私有/保留网络，防止 SSRF。

    Args:
        url: 待校验的完整 URL。
        allow_localhost: 开发模式下允许 localhost（默认拒绝）。

    Returns:
        传入的 url（校验通过）。

    Raises:
        ValueError: URL 格式异常或指向私有网络。
    """
    url = url.strip()
    if not url:
        raise ValueError("URL 不能为空")

    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise ValueError(f"仅允许 http/https 协议，当前为 {scheme!r}")

    host = parsed.hostname
    if not host:
        raise ValueError("URL 缺少主机名")

    # 阻止明显危险的主机名
    _blocked_hosts = {"localhost", "metadata.google.internal", "metadata"}
    if not allow_localhost and host.lower() in _blocked_hosts:
        raise ValueError(f"不允许访问 {host!r}")

    # 阻止 IP 直连私有网络
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
            raise ValueError(f"不允许访问私有/保留网络地址 {host!r}")
    except ValueError:
        # host 不是 IP 格式（是域名），继续检查
        pass

    # 阻止以点开头的域名或纯数字域名（可能是 IP 变体）
    if re.match(r"^[\d.]+$", host):
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
                raise ValueError(f"不允许访问私有/保留网络地址 {host!r}")
        except ValueError as exc:
            if "私有" in str(exc) or "保留" in str(exc):
                raise

    return url
