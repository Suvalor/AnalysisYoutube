"""
LLM 客户端工厂：根据 protocol 字段选择 Anthropic SDK 或 OpenAI SDK。

protocol=anthropic（默认）→ Anthropic Messages API
protocol=openai          → OpenAI chat.completions API（兼容网关）
"""

from __future__ import annotations

import logging

from dataclasses import dataclass
from typing import AsyncIterator, Any

import httpx
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)


def normalize_base_url(url: str | None) -> str:
    """去掉首尾空白与末尾斜杠。"""
    return (url or "").strip().rstrip("/")


@dataclass(frozen=True)
class LLMClientConfig:
    api_key: str
    base_url: str
    model_name: str | None = None
    protocol: str = "anthropic"  # anthropic / openai


class LLMClientFactory:
    """
    LLM 客户端工厂（协议感知 + async streaming 支持）。

    根据 cfg.protocol 选择 SDK：
    - anthropic：使用 Anthropic SDK 调用 Messages API
    - openai：使用 OpenAI SDK 调用 chat.completions API
    """

    def __init__(
        self,
        *,
        default_timeout_seconds: float = 120.0,
        max_connections: int = 30,
        max_keepalive_connections: int = 10,
    ) -> None:
        self._timeout = default_timeout_seconds
        self._limits = httpx.Limits(max_connections=max_connections, max_keepalive_connections=max_keepalive_connections)

    def resolve_model_name(self, cfg: LLMClientConfig) -> str:
        return (cfg.model_name or "").strip()

    # ── Anthropic 通道 ──

    async def _anthropic_chat(
        self,
        *,
        cfg: LLMClientConfig,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """Anthropic Messages API 非流式调用。"""
        base = normalize_base_url(cfg.base_url)
        model_name = self.resolve_model_name(cfg)
        if not model_name:
            raise ValueError("Anthropic 协议要求 model_name 不能为空")

        http_client = httpx.AsyncClient(timeout=self._timeout, limits=self._limits, trust_env=False)
        client = AsyncAnthropic(api_key=cfg.api_key, base_url=base or None, http_client=http_client)
        try:
            system_prompt, filtered = _split_system_prompt(messages)
            resp = await client.messages.create(
                model=model_name,
                max_tokens=kwargs.pop("max_tokens", 4096),
                temperature=temperature,
                system=system_prompt or None,
                messages=filtered,
            )
            return resp.content[0].text if resp.content else ""
        finally:
            await http_client.aclose()

    async def _anthropic_stream(
        self,
        *,
        cfg: LLMClientConfig,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Anthropic Messages API 流式调用。"""
        base = normalize_base_url(cfg.base_url)
        model_name = self.resolve_model_name(cfg)
        if not model_name:
            raise ValueError("Anthropic 协议要求 model_name 不能为空")

        http_client = httpx.AsyncClient(timeout=self._timeout, limits=self._limits, trust_env=False)
        client = AsyncAnthropic(api_key=cfg.api_key, base_url=base or None, http_client=http_client)
        try:
            system_prompt, filtered = _split_system_prompt(messages)
            stream = await client.messages.create(
                model=model_name,
                max_tokens=kwargs.pop("max_tokens", 4096),
                temperature=temperature,
                system=system_prompt or None,
                messages=filtered,
                stream=True,
            )
            async for event in stream:
                if event.type == "content_block_delta" and hasattr(event, "delta"):
                    text = getattr(event.delta, "text", None)
                    if text:
                        yield text
        finally:
            await http_client.aclose()

    # ── OpenAI 通道 ──

    async def _openai_chat(
        self,
        *,
        cfg: LLMClientConfig,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """OpenAI chat.completions 非流式调用。"""
        base = normalize_base_url(cfg.base_url)
        model_name = self.resolve_model_name(cfg)
        if not model_name:
            raise ValueError("OpenAI 协议要求 model_name 不能为空")

        http_client = httpx.AsyncClient(timeout=self._timeout, limits=self._limits, trust_env=False)
        client = AsyncOpenAI(api_key=cfg.api_key, base_url=base, http_client=http_client)
        try:
            resp = await client.chat.completions.create(
                model=model_name,
                stream=False,
                messages=messages,
                temperature=temperature,
                **kwargs,
            )
            choice = resp.choices[0] if resp.choices else None
            return (choice.message.content if choice and choice.message else "") or ""
        finally:
            await http_client.aclose()

    async def _openai_stream(
        self,
        *,
        cfg: LLMClientConfig,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """OpenAI chat.completions 流式调用。"""
        base = normalize_base_url(cfg.base_url)
        model_name = self.resolve_model_name(cfg)
        if not model_name:
            raise ValueError("OpenAI 协议要求 model_name 不能为空")

        http_client = httpx.AsyncClient(timeout=self._timeout, limits=self._limits, trust_env=False)
        client = AsyncOpenAI(api_key=cfg.api_key, base_url=base, http_client=http_client)
        try:
            stream = await client.chat.completions.create(
                model=model_name,
                stream=True,
                messages=messages,
                temperature=temperature,
                **kwargs,
            )
            async for chunk in stream:
                delta_text = _extract_openai_delta(chunk)
                if delta_text:
                    yield delta_text
        finally:
            await http_client.aclose()

    # ── 统一入口 ──

    async def chat_completions_content(
        self,
        *,
        cfg: LLMClientConfig,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """非流式调用：根据 protocol 选择 SDK。"""
        if cfg.protocol == "anthropic":
            return await self._anthropic_chat(cfg=cfg, messages=messages, temperature=temperature, **kwargs)
        return await self._openai_chat(cfg=cfg, messages=messages, temperature=temperature, **kwargs)

    async def stream_chat_completions_deltas(
        self,
        *,
        cfg: LLMClientConfig,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """流式调用：根据 protocol 选择 SDK。"""
        if cfg.protocol == "anthropic":
            async for delta in self._anthropic_stream(cfg=cfg, messages=messages, temperature=temperature, **kwargs):
                yield delta
        else:
            async for delta in self._openai_stream(cfg=cfg, messages=messages, temperature=temperature, **kwargs):
                yield delta


def _split_system_prompt(messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
    """将 system 消息从 messages 中分离（Anthropic SDK 要求 system 为独立参数）。"""
    system_parts: list[str] = []
    filtered: list[dict[str, str]] = []
    for msg in messages:
        if msg.get("role") == "system":
            system_parts.append(msg.get("content", ""))
        else:
            filtered.append(msg)
    return "\n\n".join(system_parts), filtered


def _extract_openai_delta(chunk: Any) -> str:
    """从 OpenAI streaming chunk 中提取增量文本。"""
    try:
        choices = getattr(chunk, "choices", None)
        if not choices:
            return ""
        first = choices[0]
        delta = getattr(first, "delta", None)
        if delta is None:
            return ""
        content = getattr(delta, "content", None)
        if isinstance(content, str) and content:
            return content
        text = getattr(delta, "text", None)
        if isinstance(text, str) and text:
            return text
        message = getattr(delta, "message", None)
        msg_content = getattr(message, "content", None) if message is not None else None
        if isinstance(msg_content, str) and msg_content:
            return msg_content
        return ""
    except Exception:
        return ""
