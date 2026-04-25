"""趋势缓存服务：读写 trend_cache + trend_history。"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trend_cache import TrendCache, TrendHistory

logger = logging.getLogger(__name__)

TREND_CACHE_TTL = timedelta(hours=1)
MAX_HISTORY_PER_USER = 10


async def get_cached_trend(
    db: AsyncSession,
    *,
    region: str,
    category_id: str,
) -> dict | None:
    """获取趋势缓存，1小时内有效则返回，否则返回 None。"""
    today = date.today()
    stmt = select(TrendCache).where(
        TrendCache.cache_date == today,
        TrendCache.region == region,
        TrendCache.category_id == category_id,
    )
    result = await db.execute(stmt)
    cache = result.scalar_one_or_none()
    if cache is None:
        return None
    # 检查是否过期
    now = datetime.now(timezone.utc)
    if cache.updated_at.tzinfo is None:
        updated = cache.updated_at.replace(tzinfo=timezone.utc)
    else:
        updated = cache.updated_at
    if now - updated > TREND_CACHE_TTL:
        return None
    try:
        return json.loads(cache.data)
    except json.JSONDecodeError:
        logger.warning("趋势缓存数据损坏: region=%s, category_id=%s", region, category_id)
        return None


async def save_trend_cache(
    db: AsyncSession,
    *,
    region: str,
    category_id: str,
    data: dict,
) -> None:
    """保存趋势缓存（upsert）。"""
    today = date.today()
    stmt = select(TrendCache).where(
        TrendCache.cache_date == today,
        TrendCache.region == region,
        TrendCache.category_id == category_id,
    )
    result = await db.execute(stmt)
    cache = result.scalar_one_or_none()
    json_data = json.dumps(data, ensure_ascii=False)
    if cache:
        cache.data = json_data
        cache.updated_at = datetime.now(timezone.utc)
    else:
        cache = TrendCache(
            cache_date=today,
            region=region,
            category_id=category_id,
            data=json_data,
        )
        db.add(cache)
    await db.flush()


async def add_trend_history(
    db: AsyncSession,
    *,
    user_id: int,
    region: str,
    category_id: str,
    region_label: str,
    category_label: str,
) -> None:
    """添加趋势历史记录，保留最近10条。"""
    today = date.today()
    # 检查是否已有相同维度记录（同一天+地区+品类）
    stmt = select(TrendHistory).where(
        TrendHistory.user_id == user_id,
        TrendHistory.cache_date == today,
        TrendHistory.region == region,
        TrendHistory.category_id == category_id,
    )
    result = await db.execute(stmt)
    existing = result.scalars().first()
    if existing:
        # 已存在则更新时间
        existing.created_at = datetime.now(timezone.utc)
        await db.flush()
        return

    # 新增记录
    history = TrendHistory(
        user_id=user_id,
        cache_date=today,
        region=region,
        category_id=category_id,
        region_label=region_label,
        category_label=category_label,
    )
    db.add(history)
    await db.flush()

    # 清理超出10条的旧记录
    count_stmt = select(func.count()).select_from(TrendHistory).where(
        TrendHistory.user_id == user_id,
    )
    total = (await db.execute(count_stmt)).scalar() or 0
    if total > MAX_HISTORY_PER_USER:
        # 删除最旧的记录
        del_stmt = (
            select(TrendHistory)
            .where(TrendHistory.user_id == user_id)
            .order_by(TrendHistory.created_at.asc())
            .limit(total - MAX_HISTORY_PER_USER)
        )
        del_result = await db.execute(del_stmt)
        for old in del_result.scalars().all():
            await db.delete(old)
        await db.flush()


async def list_trend_history(
    db: AsyncSession,
    *,
    user_id: int,
    limit: int = 10,
) -> list[TrendHistory]:
    """获取用户趋势历史记录。"""
    stmt = (
        select(TrendHistory)
        .where(TrendHistory.user_id == user_id)
        .order_by(TrendHistory.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
