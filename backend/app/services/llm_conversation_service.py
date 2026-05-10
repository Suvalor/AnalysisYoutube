"""LLM 对话历史服务：加载历史、截断超长消息、保存对话轮次、自动淘汰。"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.llm_conversation import (
    get_max_turn,
    list_messages_by_entity,
    prune_old_turns,
    save_message,
)

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_MAX_TURNS = 20
# 粗略 token 估算：4 字符 ≈ 1 token（中英混合场景偏保守）
CHARS_PER_TOKEN = 4
DEFAULT_MAX_CHARS = 8000  # 约 2000 tokens


def _truncate_messages(
    messages: list[dict[str, str]],
    max_chars: int = DEFAULT_MAX_CHARS,
) -> list[dict[str, str]]:
    """
    从最早的消息开始截断，确保总字符数不超过 max_chars。
    始终保留 system 消息（如有）和最后一条 user 消息。
    """
    if not messages:
        return messages

    total_chars = sum(len(m.get("content", "")) for m in messages)
    if total_chars <= max_chars:
        return messages

    # 分离 system / 非system
    system_msgs = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]

    # 始终保留 system + 最后一条
    keep_tail = 1 if non_system else 0
    kept_chars = sum(len(m.get("content", "")) for m in system_msgs)
    if non_system:
        kept_chars += len(non_system[-1].get("content", ""))

    # 从非 system 的头部开始丢弃，直到总字符数 <= max_chars
    result_non_system: list[dict[str, str]] = []
    if non_system:
        result_non_system.append(non_system[-1])  # 保留最后一条

    # 从倒数第二条往前加，直到超限
    for m in reversed(non_system[:-1]):
        m_chars = len(m.get("content", ""))
        if kept_chars + m_chars > max_chars:
            break
        result_non_system.insert(0, m)
        kept_chars += m_chars

    return system_msgs + result_non_system


async def load_conversation_messages(
    session: AsyncSession,
    *,
    user_id: int,
    entity_type: str,
    entity_id: str,
    max_turns: int = DEFAULT_MAX_TURNS,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> list[dict[str, str]]:
    """
    加载对话历史并转为 LLM 消息格式。
    自动截断超长消息以控制 token 预算。
    """
    rows = await list_messages_by_entity(
        session,
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        max_turns=max_turns,
    )
    messages = [{"role": r.role, "content": r.content} for r in rows]
    return _truncate_messages(messages, max_chars=max_chars)


async def save_conversation_turn(
    session: AsyncSession,
    *,
    user_id: int,
    entity_type: str,
    entity_id: str,
    user_content: str,
    assistant_content: str,
    system_content: str | None = None,
    model_name: str | None = None,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> int:
    """
    保存一轮对话（system + user + assistant），返回当前轮次号。
    自动淘汰超过 max_turns 的最早轮次。
    """
    current_max = await get_max_turn(
        session,
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    next_turn = current_max + 1

    # 首轮保存 system 提示词
    if system_content and next_turn == 1:
        await save_message(
            session,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            role="system",
            content=system_content,
            turn=0,
            model_name=model_name,
        )

    await save_message(
        session,
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        role="user",
        content=user_content,
        turn=next_turn,
        model_name=model_name,
    )
    await save_message(
        session,
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        role="assistant",
        content=assistant_content,
        turn=next_turn,
        model_name=model_name,
    )

    # 自动淘汰
    deleted = await prune_old_turns(
        session,
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        keep_turns=max_turns,
    )
    if deleted > 0:
        logger.info(
            "淘汰旧对话 user_id=%s entity=%s/%s deleted=%d",
            user_id, entity_type, entity_id, deleted,
        )

    return next_turn
