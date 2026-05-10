"""全局速率限制配置（基于 slowapi）。"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# 按 IP 限流；若部署在反向代理后，需配置 X-Forwarded-For 解析
limiter = Limiter(key_func=get_remote_address)
