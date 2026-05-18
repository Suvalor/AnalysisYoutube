"""结构化请求/响应日志中间件。

- INFO 级别：只记录 method path status duration
- DEBUG 级别：额外记录请求 body 和响应 body（敏感字段自动脱敏）
"""

import json
import logging
import re
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

logger = logging.getLogger("request")

# ── 脱敏 ──────────────────────────────────────────────
_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "confirm_password",
        "new_password",
        "old_password",
        "api_key",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "api_key_encrypted",
        "client_secret",
        "secret_key",
        "access_key_secret",
    }
)

_MASK_PATTERN = re.compile(
    r"""(?x)
    (
        " (?: """ + "|".join(_SENSITIVE_KEYS) + r""") \s*:\s*"
    )
    [^"]*?
    ( " )
    """,
    re.IGNORECASE,
)


def _mask_sensitive(raw: str) -> str:
    return _MASK_PATTERN.sub(r'\1***\2', raw)


# ── body 处理 ─────────────────────────────────────────
_MAX_BODY_LOG = 10_000  # 超过此字节数的 body 不记录
_BODY_PREVIEW = 500


def _safe_body(body: bytes, content_type: str = "") -> str:
    if not body:
        return ""
    if len(body) > _MAX_BODY_LOG:
        return f"<body too large: {len(body)} bytes>"
    text = body.decode("utf-8", errors="replace")
    if "application/json" in content_type:
        try:
            parsed = json.loads(text)
            text = json.dumps(parsed, ensure_ascii=False)
        except (json.JSONDecodeError, ValueError):
            pass
    return _mask_sensitive(text)


# ── 路径排除 ──────────────────────────────────────────
_SKIP_PATHS = frozenset({"/docs", "/redoc", "/openapi.json", "/favicon.ico"})
_SKIP_PREFIXES = ("/static/", "/assets/")


def _should_skip(path: str) -> bool:
    if path in _SKIP_PATHS:
        return True
    return any(path.startswith(p) for p in _SKIP_PREFIXES)


# ── 中间件 ────────────────────────────────────────────
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if _should_skip(request.url.path):
            return await call_next(request)

        start = time.perf_counter()

        # 读取请求 body（需要在 call_next 之前读取，因为 body stream 只能消费一次）
        request_body = b""
        if request.method in ("POST", "PUT", "PATCH"):
            request_body = await request.body()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start) * 1000

        # INFO：只记录请求行
        logger.info(
            "%s %s %d %.0fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        # DEBUG：额外记录 body
        if logger.isEnabledFor(logging.DEBUG):
            req_body = _safe_body(request_body, request.headers.get("content-type", ""))
            if req_body:
                logger.debug("  → body: %s", req_body)

            # 读取响应 body（仅对非流式响应）
            if not isinstance(response, StreamingResponse):
                resp_body = b""
                async for chunk in response.body_iterator:
                    resp_body += chunk
                # 重建 response，因为 body_iterator 已被消费
                response = Response(
                    content=resp_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )
                resp_text = _safe_body(resp_body, response.media_type or "")
                if resp_text:
                    logger.debug(
                        "  ← %d %.0fms body: %s",
                        response.status_code,
                        duration_ms,
                        resp_text,
                    )

        return response
