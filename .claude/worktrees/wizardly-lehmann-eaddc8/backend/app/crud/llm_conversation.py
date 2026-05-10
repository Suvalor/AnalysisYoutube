"""LLM 对话历史 CRUD 操作。"""

from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_conversation import LLMConversation


async def list_messages_by_entity(
    session: AsyncSession,
    *,
    user_id: int,
    entity_type: str,
    entity_id: str,
    max_turns: int = 20,
) -> list[LLMConversation]:
    """按业务实体加载对话历史，按 turn 升序。"""
    stmt = (
        select(LLMConversation)
        .where(
            LLMConversation.user_id == user_id,
            LLMConversation.entity_type == entity_type,
            LLMConversation.entity_id == entity_id,
        )
        .order_by(LLMConversation.turn.asc(), LLMConversation.id.asc())
    )
    result = await session.execute(stmt)
    rows = list(result.scalars().all())
    # 按 max_turns 截断：只保留最近 max_turns 轮
    if rows:
        max_turn = max(r.turn for r in rows)
        min_keep_turn = max(0, max_turn - max_turns + 1)
        rows = [r for r in rows if r.turn >= min_keep_turn]
    return rows


async def save_message(
    session: AsyncSession,
    *,
    user_id: int,
    entity_type: str,
    entity_id: str,
    role: str,
    content: str,
    turn: int,
    model_name: str | None = None,
) -> LLMConversation:
    """保存单条对话消息。"""
    row = LLMConversation(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        role=role,
        content=content,
        turn=turn,
        model_name=model_name,
    )
    session.add(row)
    await session.flush()
    return row


async def get_max_turn(
    session: AsyncSession,
    *,
    user_id: int,
    entity_type: str,
    entity_id: str,
) -> int:
    """获取当前最大轮次号。"""
    stmt = (
        select(LLMConversation.turn)
        .where(
            LLMConversation.user_id == user_id,
            LLMConversation.entity_type == entity_type,
            LLMConversation.entity_id == entity_id,
        )
        .order_by(LLMConversation.turn.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    val = result.scalar_one_or_none()
    return val if val is not None else 0


async def prune_old_turns(
    session: AsyncSession,
    *,
    user_id: int,
    entity_type: str,
    entity_id: str,
    keep_turns: int = 20,
) -> int:
    """淘汰最早轮次，保留最近 keep_turns 轮。返回删除行数。"""
    max_t = await get_max_turn(
        session,
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    if max_t < keep_turns:
        return 0
    cutoff = max_t - keep_turns + 1
    stmt = (
        sa_delete(LLMConversation)
        .where(
            LLMConversation.user_id == user_id,
            LLMConversation.entity_type == entity_type,
            LLMConversation.entity_id == entity_id,
            LLMConversation.turn < cutoff,
        )
    )
    result = await session.execute(stmt)
    return result.rowcount
