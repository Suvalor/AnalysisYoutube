"""
OpenAI 兼容 LLM 的协议感知与客户端构建。

根据配置中的 Base URL 动态选择行为，避免在业务代码中散落 if-else。
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass
from typing import AsyncIterator, Any

import httpx
from openai import AsyncOpenAI

from app.services.config_manager import ResolvedIntegrationConfig


def normalize_openai_base_url(url: str | None) -> str:
    """去掉首尾空白与末尾斜杠，便于与规范地址比较。"""
    return (url or "").strip().rstrip("/")


# 火山引擎 Coding Plan（OpenAI 兼容）规范 Base URL，须与控制台文档一致
VOLCENGINE_CODING_OPENAI_BASE_URL_CANONICAL = "https://ark.cn-beijing.volces.com/api/coding/v3"

# Coding Plan 下未指定模型时使用的默认 model 参数（可被集成配置中的 Endpoint 覆盖）
VOLCENGINE_CODING_DEFAULT_MODEL_ID = "ark-code-latest"


class LlmOpenAiProtocolKind(str, Enum):
    """当前请求所采用的 OpenAI 兼容协议变体。"""

    STANDARD = "standard"
    """标准 OpenAI Compatible：不修改 model 与 Header，仅透传 SDK 默认行为。"""

    VOLCENGINE_CODING_V3 = "volcengine_coding_v3"
    """火山引擎 Coding Plan：/api/coding/v3，未指定 model 时使用 ark-code-latest 或集成 Endpoint。"""


def detect_openai_protocol_kind(base_url: str | None) -> LlmOpenAiProtocolKind:
    """仅依据 Base URL 判断协议类型（不读环境变量硬编码开关）。"""
    u = normalize_openai_base_url(base_url)
    if u == VOLCENGINE_CODING_OPENAI_BASE_URL_CANONICAL:
        return LlmOpenAiProtocolKind.VOLCENGINE_CODING_V3
    return LlmOpenAiProtocolKind.STANDARD


def is_volcengine_coding_plan_openai_api(base_url: str | None) -> bool:
    return detect_openai_protocol_kind(base_url) == LlmOpenAiProtocolKind.VOLCENGINE_CODING_V3


def resolve_openai_chat_model_parameter(
    base_url: str,
    explicit_model: str,
    integration: ResolvedIntegrationConfig | None,
) -> str:
    """
    解析 chat.completions 的 model 参数。

    - Coding Plan URL：显式非空则用显式值；否则优先集成中的 volcengine_endpoint_id，再回退 ark-code-latest。
    - 火山方舟常规 OpenAI 路径（非 Coding）：保留 ep- 接入点回退逻辑。
    - 其他 URL：标准模式，显式优先，否则回退集成 endpoint_id。
    """
    # 按最新要求：
    # - 仅当 base_url 为 Coding Plan 时才做非标准适配：model_name 为空则默认 ark-code-latest
    # - 其它 URL 维持“原汁原味”：不对 model_name 做任何默认填充/重写
    _ = integration  # 当前解析逻辑不使用 integration，仅保留参数兼容
    u = normalize_openai_base_url(base_url)
    ex = (explicit_model or "").strip()
    if is_volcengine_coding_plan_openai_api(u):
        return ex if ex else VOLCENGINE_CODING_DEFAULT_MODEL_ID
    return ex


def create_async_openai_client(
    *,
    api_key: str,
    base_url: str,
    timeout: float | None = 120.0,
    limits: httpx.Limits | None = None,
) -> tuple[AsyncOpenAI, httpx.AsyncClient]:
    """
    构建 AsyncOpenAI 与底层 httpx 客户端。

    调用方必须在用毕后执行 ``await http_client.aclose()``（标准 OpenAI 兼容模式同样适用）。
    """
    normalized = normalize_openai_base_url(base_url)
    http_client = httpx.AsyncClient(timeout=timeout, limits=limits, trust_env=False)
    client = AsyncOpenAI(api_key=api_key, base_url=normalized, http_client=http_client)
    return client, http_client


@dataclass(frozen=True)
class LLMClientConfig:
    api_key: str
    base_url: str
    model_name: str | None = None


class LLMClientFactory:
    """
    OpenAI 兼容 LLM 客户端工厂（协议感知 + async streaming 支持）。

    核心原则：
    - 仅依据 base_url 是否为 Coding Plan 才触发非标准逻辑
    - Coding Plan：model_name 为空 => 默认 ark-code-latest
    - 其它：严格尊重 model_name，不做任何默认填充或重写
    """

    def __init__(
        self,
        *,
        standard_timeout_seconds: float = 120.0,
        coding_plan_timeout_seconds: float | None = None,
        max_connections: int = 30,
        max_keepalive_connections: int = 10,
    ) -> None:
        self._standard_timeout = standard_timeout_seconds
        self._coding_plan_timeout = coding_plan_timeout_seconds
        self._limits = httpx.Limits(max_connections=max_connections, max_keepalive_connections=max_keepalive_connections)

    def resolve_model_name(self, cfg: LLMClientConfig) -> str:
        base = normalize_openai_base_url(cfg.base_url)
        model = (cfg.model_name or "").strip()
        # 复用现有 resolve_openai_chat_model_parameter 的规则：Coding Plan 才注入默认
        return resolve_openai_chat_model_parameter(base, model, integration=None)

    def detect_is_coding_plan(self, cfg: LLMClientConfig) -> bool:
        return is_volcengine_coding_plan_openai_api(cfg.base_url)

    def _extract_delta_text(self, chunk: Any, *, is_coding_plan: bool) -> str:
        """
        流式数据清洗器：尽可能从 chunk 里抽取增量文本。
        目标：把潜在字段差异（content/text/message/content 等）归一到字符串。
        """
        try:
            choices = getattr(chunk, "choices", None)
            if not choices:
                return ""
            first = choices[0]
            delta = getattr(first, "delta", None)
            if delta is None:
                return ""

            # 标准：delta.content
            content = getattr(delta, "content", None)
            if isinstance(content, str) and content:
                return content

            # 兼容：delta.text
            text = getattr(delta, "text", None)
            if isinstance(text, str) and text:
                return text

            # 兼容：delta.message.content
            message = getattr(delta, "message", None)
            msg_content = getattr(message, "content", None) if message is not None else None
            if isinstance(msg_content, str) and msg_content:
                return msg_content

            # Coding Plan：delta 可能是 dict 或嵌套对象
            if is_coding_plan and isinstance(delta, dict):
                v = delta.get("content") or delta.get("text")
                if isinstance(v, str) and v:
                    return v
                message_obj = delta.get("message")
                if isinstance(message_obj, dict):
                    v2 = message_obj.get("content") or message_obj.get("text")
                    if isinstance(v2, str) and v2:
                        return v2

            # 其它情况：返回空（不影响 SSE 协议，只是不产出 delta）
            return ""
        except Exception:
            return ""

    async def stream_chat_completions_deltas(
        self,
        *,
        cfg: LLMClientConfig,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        # 允许未来扩展：例如 max_tokens
        **create_kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        流式调用：返回 async iterator，逐 chunk 产出增量文本。
        注意：函数内部负责正确关闭 http_client，保证并发与资源释放。
        """
        base = normalize_openai_base_url(cfg.base_url)
        is_coding_plan = self.detect_is_coding_plan(cfg)
        timeout = self._coding_plan_timeout if is_coding_plan else self._standard_timeout

        model_name = self.resolve_model_name(cfg)
        if not model_name:
            raise ValueError("model_name 不能为空（Coding Plan 可留空以使用默认 ark-code-latest）")

        http_client = httpx.AsyncClient(timeout=timeout, limits=self._limits, trust_env=False)
        client = AsyncOpenAI(api_key=cfg.api_key, base_url=base, http_client=http_client)
        try:
            stream = await client.chat.completions.create(
                model=model_name,
                stream=True,
                messages=messages,
                temperature=temperature,
                **create_kwargs,
            )
            async for chunk in stream:
                delta_text = self._extract_delta_text(chunk, is_coding_plan=is_coding_plan)
                if delta_text:
                    yield delta_text
        finally:
            await http_client.aclose()

    async def chat_completions_content(
        self,
        *,
        cfg: LLMClientConfig,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        **create_kwargs: Any,
    ) -> str:
        """非流式调用：返回 choices[0].message.content 的文本。"""
        base = normalize_openai_base_url(cfg.base_url)
        is_coding_plan = self.detect_is_coding_plan(cfg)
        timeout = self._coding_plan_timeout if is_coding_plan else self._standard_timeout
        http_client = httpx.AsyncClient(timeout=timeout, limits=self._limits, trust_env=False)
        client = AsyncOpenAI(api_key=cfg.api_key, base_url=base, http_client=http_client)
        try:
            resp = await client.chat.completions.create(
                model=self.resolve_model_name(cfg),
                stream=False,
                messages=messages,
                temperature=temperature,
                **create_kwargs,
            )
            choice = resp.choices[0] if resp.choices else None
            raw_content = (choice.message.content if choice and choice.message else "") or ""
            return raw_content
        finally:
            await http_client.aclose()
