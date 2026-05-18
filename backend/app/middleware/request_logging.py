"""结构化请求/响应日志中间件（纯 ASGI 实现）。

- INFO 级别：只记录 method path status duration
- DEBUG 级别：额外记录请求 body 和响应 body（敏感字段自动脱敏）

不使用 BaseHTTPMiddleware，避免其在异常路径下创建新 Response 对象
导致 CORSMiddleware 已添加的 Access-Control-* 头被丢弃的问题。
"""

import json
import logging
import re
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

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
_MAX_BODY_LOG = 10_000


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
_SKIP_PATHS = frozenset({"/docs", "/redoc", "/openapi.json", "/favicon.ico", "/health"})
_SKIP_PREFIXES = ("/static/", "/assets/")


def _should_skip(path: str) -> bool:
    if path in _SKIP_PATHS:
        return True
    return any(path.startswith(p) for p in _SKIP_PREFIXES)


# ── 中间件 ────────────────────────────────────────────
class RequestLoggingMiddleware:
    """纯 ASGI 中间件：结构化请求/响应日志。

    不使用 BaseHTTPMiddleware，避免 CORS preflight 响应头丢失问题。
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if _should_skip(path):
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        start = time.perf_counter()

        # ── 捕获请求 body ──
        request_body = b""
        if method in ("POST", "PUT", "PATCH"):
            # 读取 body 并缓存，下游仍可消费
            body_messages: list[Message] = []
            while True:
                message = await receive()
                body_messages.append(message)
                if message["type"] == "http.request.body":
                    request_body += message.get("body", b"")
                    if not message.get("more_body", False):
                        break
                else:
                    break

            # 构造新的 receive，让下游仍能读到 body
            async def _receive() -> Message:
                if body_messages:
                    return body_messages.pop(0)
                return {"type": "http.disconnect"}

            inner_receive = _receive
        else:
            inner_receive = receive

        # ── 捕获响应 ──
        status_code = 0
        response_headers: list[tuple[bytes, bytes]] = []
        response_body = b""
        response_started = False

        async def _send(message: Message) -> None:
            nonlocal status_code, response_headers, response_body, response_started

            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
                response_headers = list(message.get("headers", []))
                response_started = True
                await send(message)
                return

            if message["type"] == "http.response.body":
                response_body += message.get("body", b"")
                await send(message)
                return

            await send(message)

        # ── 执行下游 ──
        await self.app(scope, inner_receive, _send)

        duration_ms = (time.perf_counter() - start) * 1000

        # ── INFO：请求行 ──
        logger.info("%s %s %d %.0fms", method, path, status_code, duration_ms)

        # ── DEBUG：请求/响应 body ──
        if logger.isEnabledFor(logging.DEBUG):
            headers_dict = {
                k.decode("latin-1").lower(): v.decode("latin-1")
                for k, v in scope.get("headers", [])
            }
            req_ct = headers_dict.get("content-type", "")
            req_body = _safe_body(request_body, req_ct)
            if req_body:
                logger.debug("  → body: %s", req_body)

            # 从响应头推断 content-type
            resp_ct = ""
            for k, v in response_headers:
                if k.decode("latin-1").lower() == "content-type":
                    resp_ct = v.decode("latin-1")
                    break
            resp_text = _safe_body(response_body, resp_ct)
            if resp_text:
                logger.debug("  ← %d %.0fms body: %s", status_code, duration_ms, resp_text)