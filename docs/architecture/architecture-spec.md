# 敏感信息接口安全加固 -- 架构契约

## 一、基准探查摘要

### 1.1 P0 漏洞确认

`GET /api/users/me/integration-settings` 接口（路由文件 `backend/app/api/v1/integration_settings.py`）的 `_to_read` 函数（第41-67行）直接将 `merge_integration_config` 返回的完整密钥明文赋值给 `IntegrationSettingsRead` schema，**从未调用同文件第37-38行已定义的 `_secret_display` 函数**。以下字段在 GET 响应中以明文泄露：

- `youtube_api_key`
- `aliyun_access_key_secret`
- `tencent_cos_secret_key`
- `volc_cv_secret_access_key`

此外，`aliyun_access_key_id`、`tencent_cos_secret_id`、`volc_cv_access_key_id` 虽不在 `SECRET_PAYLOAD_KEYS` 中，但属于半敏感凭证（Access Key ID），也应脱敏。

### 1.2 现有安全基线（已有，可复用）

| 已有机制 | 位置 | 状态 |
|----------|------|------|
| `_secret_display` 函数 | `integration_settings.py:37-38` | 已定义，未调用 |
| `SECRET_PAYLOAD_KEYS` 常量 | `config_manager.py:43-50` | 已定义，仅用于 PUT 写入过滤 |
| 422 验证错误脱敏 | `main.py:17,41-52` | 已生效，过滤 password/new_password/confirm_password |
| Security Headers Middleware | `main.py:84-114` | 已生效 |
| 字段加密服务 | `field_encryption.py` | 已生效，用于 AI API Key |
| Pydantic `repr=False` | `schemas/auth.py:10,62,93` | 已设置，防止密码出现在 repr |

### 1.3 缺失项

| 缺失项 | 风险等级 |
|--------|----------|
| HTTPS 强制中间件 | P1 |
| 日志敏感字段过滤 | P1 |
| 前端 autocomplete 属性 | P2 |
| 前端 token 存储方式（localStorage） | P2（已知取舍，暂不改动） |

---

## 二、ADR 决策记录

### ADR-1: 集成配置密钥脱敏策略

- **背景**：`_to_read` 直接传递明文密钥，`_secret_display` 已存在但未调用
- **决策**：修改 `_to_read` 函数，对 `SECRET_PAYLOAD_KEYS` 中的字段调用 `_secret_display` 进行脱敏；同时将 `aliyun_access_key_id`、`tencent_cos_secret_id`、`volc_cv_access_key_id` 纳入半敏感字段，显示后4位（格式 `****abcd`）
- **论证**：
  - 方案A（全掩码 `********`）：简单但前端无法区分已配置/未配置，且用户无法确认是哪个 key
  - 方案B（后4位 `****abcd`）：兼顾安全与可用性，用户可辨识已配置的 key
  - 选择方案B。`SECRET_PAYLOAD_KEYS` 中的字段（secret 类）用全掩码 `********`，Access Key ID 类用后4位 `****abcd`
- **风险**：前端若依赖明文 key 做回填逻辑，改为脱敏后需确保 PUT 时能正确跳过占位符（已有 `is_secret_placeholder` 逻辑覆盖）

### ADR-2: HTTPS 强制中间件实现方式

- **背景**：生产环境需强制 HTTPS，开发环境 localhost 需豁免
- **决策**：在 `main.py` 中新增纯 ASGI 中间件 `HTTPSRedirectMiddleware`，与现有 `SecurityHeadersMiddleware` 同级，检测非 HTTPS 请求返回 301 重定向；localhost / 127.0.0.1 豁免
- **论证**：
  - 方案A（Starlette 内置 `HTTPSRedirectMiddleware`）：不提供 localhost 豁免，开发环境无法使用
  - 方案B（自定义 ASGI 中间件）：可精确控制豁免逻辑，与现有 `SecurityHeadersMiddleware` 风格一致
  - 选择方案B
- **风险**：反向代理（Nginx/Cloudflare）已终止 HTTPS 时，需确保 `X-Forwarded-Proto` 头被正确识别，否则会误重定向

### ADR-3: 日志敏感字段过滤方案

- **背景**：当前 34 个文件使用 `logging`，无统一过滤机制；经审计，现有 logger 调用均未直接记录密码/密钥明文，但缺乏防御性保障
- **决策**：在 `app/core/` 下新增 `log_filter.py`，提供 `SensitiveDataFilter`（`logging.Filter` 子类），注册到 root logger；过滤规则基于字段名模式匹配
- **论证**：
  - 方案A（逐文件审查修改）：34 个文件逐一修改，维护成本高，容易遗漏
  - 方案B（全局 logging Filter）：一处注册，全局生效，新增 logger 自动覆盖
  - 选择方案B
- **风险**：过滤可能误伤非敏感的同名变量（如 `password` 出现在非密码上下文），但采用正则匹配完整单词可降低风险

### ADR-4: 前端 token 存储方式

- **背景**：当前 JWT 存储在 `localStorage`，存在 XSS 窃取风险
- **决策**：本次不改动。理由：改为 `httpOnly` cookie 需要后端配合修改认证流程（CSRF 防护、cookie 设置、登录接口返回方式），属于 L3 级改动，超出"最小改动"范围
- **论证**：当前已有 CSP Header 缓解 XSS 风险，且 token 有过期机制
- **风险**：XSS 攻击仍可窃取 token。建议作为下一迭代专项处理

---

## 三、模块物理划分与修改清单

### 3.1 后端修改

| 文件路径 | 修改点 | 改动量 |
|----------|--------|--------|
| `backend/app/api/v1/integration_settings.py` | 修改 `_to_read` 函数，对敏感/半敏感字段调用脱敏函数 | ~15行 |
| `backend/app/api/v1/integration_settings.py` | 新增 `_semi_secret_display` 函数（显示后4位） | ~5行 |
| `backend/app/services/config_manager.py` | 新增 `SEMI_SECRET_PAYLOAD_KEYS` 常量 | ~5行 |
| `backend/app/core/log_filter.py` | 新建文件：`SensitiveDataFilter` | ~40行 |
| `backend/app/main.py` | 注册 `SensitiveDataFilter` 到 root logger | ~5行 |
| `backend/app/main.py` | 新增 `HTTPSRedirectMiddleware` | ~35行 |

### 3.2 前端修改

| 文件路径 | 修改点 | 改动量 |
|----------|--------|--------|
| `frontend/src/pages/auth/LoginPage.tsx` | 密码 Input 添加 `autoComplete="current-password"` | ~2行 |
| `frontend/src/pages/auth/RegisterPage.tsx` | 密码 Input 添加 `autoComplete="new-password"` | ~2行 |
| `frontend/src/pages/auth/ResetPasswordPage.tsx` | 新密码 Input 添加 `autoComplete="new-password"` | ~2行 |

---

## 四、严密契约定义

### 4.1 集成配置脱敏契约

```python
# backend/app/services/config_manager.py -- 新增常量
SEMI_SECRET_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {
        "aliyun_access_key_id",
        "tencent_cos_secret_id",
        "volc_cv_access_key_id",
    }
)
```

```python
# backend/app/api/v1/integration_settings.py -- 修改 _to_read 函数

# 新增：半敏感字段脱敏（显示后4位）
def _semi_secret_display(value: str) -> str:
    """对半敏感字段脱敏：保留后4位，前面用 **** 替代。"""
    if not value or len(value) <= 4:
        return "****" if value else ""
    return "****" + value[-4:]

# 修改 _to_read 函数：对 SECRET_PAYLOAD_KEYS 字段调用 _secret_display，
# 对 SEMI_SECRET_PAYLOAD_KEYS 字段调用 _semi_secret_display
```

### 4.2 HTTPS 强制中间件契约

```python
class HTTPSRedirectMiddleware:
    """纯 ASGI 中间件：非 HTTPS 请求重定向到 HTTPS。

    豁免条件：
    - scheme 为 http 且 host 为 localhost / 127.0.0.1（开发环境）
    - 请求路径为 /health（健康检查，可能走内网 HTTP）
    - X-Forwarded-Proto 头已设置为 https（反向代理终止 SSL）
    """

    EXEMPT_HOSTS: frozenset[str] = frozenset({"localhost", "127.0.0.1"})
    EXEMPT_PATHS: frozenset[str] = frozenset({"/health"})

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            headers = dict(
                (k.decode("latin-1").lower(), v.decode("latin-1"))
                for k, v in scope.get("headers", [])
            )
            scheme = headers.get("x-forwarded-proto", scope.get("scheme", "http"))
            host = headers.get("host", "").split(":")[0]
            path = scope.get("path", "")

            if (
                scheme == "http"
                and host not in self.EXEMPT_HOSTS
                and path not in self.EXEMPT_PATHS
            ):
                query = scope.get("query_string", b"").decode("latin-1")
                url = f"https://{headers.get('host', '')}{path}"
                if query:
                    url += f"?{query}"
                response_headers = [
                    (b"location", url.encode("latin-1")),
                    (b"content-length", b"0"),
                ]
                await send({
                    "type": "http.response.start",
                    "status": 301,
                    "headers": response_headers,
                })
                await send({"type": "http.response.body", "body": b""})
                return

        await self.app(scope, receive, send)
```

### 4.3 日志敏感字段过滤契约

```python
# backend/app/core/log_filter.py -- 新建文件

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
            record.msg = self._KV_PATTERN.sub(
                lambda m: m.group(1) + '=' + _REDACTED, record.msg
            )
        if record.args and isinstance(record.args, tuple):
            record.args = tuple(
                _REDACTED if isinstance(a, str) and self._KV_PATTERN.search(a) else a
                for a in record.args
            )
        return True
```

### 4.4 前端 autocomplete 契约

- LoginPage: password Input 添加 `autoComplete="current-password"`
- RegisterPage: password + confirmPassword Input 添加 `autoComplete="new-password"`
- ResetPasswordPage: new_password + confirm_password Input 添加 `autoComplete="new-password"`

---

## 五、Sprint 规划

**Sprint 1（1 个 Sprint）**

| 任务 | 优先级 | 预估工时 |
|------|--------|----------|
| P0: 修改 `_to_read` 调用脱敏函数 | P0 | 0.5h |
| P0: 新增 `_semi_secret_display` + `SEMI_SECRET_PAYLOAD_KEYS` | P0 | 0.5h |
| P1: 新增 `log_filter.py` + 注册到 root logger | P1 | 1h |
| P1: 新增 `HTTPSRedirectMiddleware` | P1 | 1h |
| P2: 前端 autocomplete 属性 | P2 | 0.5h |

---

## 六、Developer 执行核对清单

- [ ] P0: 修改后 GET 接口密钥字段返回 `********`（非明文）
- [ ] P0: 半敏感字段返回 `****abcd` 格式（非明文）
- [ ] P0: PUT 回填时 `****abcd` 格式被识别为占位符，不写入数据库
- [ ] P1: HTTP 非 localhost 返回 301；localhost 不重定向
- [ ] P1: X-Forwarded-Proto: https 时不重定向
- [ ] P1: 日志中 `password=secret123` 输出为 `password=[REDACTED]`
- [ ] P2: 浏览器中确认 autocomplete 属性已设置
- [ ] 回归：集成配置 CRUD 流程正常
