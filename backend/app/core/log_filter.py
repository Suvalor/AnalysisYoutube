import logging
import re

_KV_PATTERN = re.compile(
    r'(\b(?:password|secret_key|access_key_secret|api_key|secret_access_key|'
    r'auth_token|access_token|smtp_password)\b)'
    r'\s*[=:]\s*\S+',
    re.IGNORECASE,
)

_REDACTED = "[REDACTED]"


class SensitiveDataFilter(logging.Filter):
    """全局日志过滤器：自动脱敏日志中的敏感字段值。"""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _KV_PATTERN.sub(
                lambda m: m.group(1) + '=' + _REDACTED, record.msg
            )
        if record.args and isinstance(record.args, tuple):
            record.args = tuple(
                _REDACTED if isinstance(a, str) and _KV_PATTERN.search(a) else a
                for a in record.args
            )
        return True
