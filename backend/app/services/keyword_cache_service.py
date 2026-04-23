"""关键词缓存服务：读写 keyword_cache + keyword_history。"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.keyword_cache import KeywordCache

logger = logging.getLogger(__name__)

KEYWORD_CACHE_TTL = timedelta(days=1)


async def get_cached_keyword(
    db: AsyncSession,
    *,
    keyword: str,
    region: str,
    language: str,
) -> dict | None:
    """获取关键词缓存，1天内有效则返回，否则返回 None。"""
    today = date.today()
    stmt = select(KeywordCache).where(
        KeywordCache.cache_date == today,
        KeywordCache.keyword == keyword,
        KeywordCache.region == region,
        KeywordCache.language == language,
    )
    result = await db.execute(stmt)
    cache = result.scalar_one_or_none()
    if cache is None:
        return None
    now = datetime.now(timezone.utc)
    if cache.updated_at.tzinfo is None:
        updated = cache.updated_at.replace(tzinfo=timezone.utc)
    else:
        updated = cache.updated_at
    if now - updated > KEYWORD_CACHE_TTL:
        return None
    try:
        return json.loads(cache.data)
    except json.JSONDecodeError:
        logger.warning("关键词缓存数据损坏: keyword=%s", keyword)
        return None


async def save_keyword_cache(
    db: AsyncSession,
    *,
    keyword: str,
    region: str,
    language: str,
    data: dict,
) -> None:
    """保存关键词缓存（upsert）。"""
    today = date.today()
    stmt = select(KeywordCache).where(
        KeywordCache.cache_date == today,
        KeywordCache.keyword == keyword,
        KeywordCache.region == region,
        KeywordCache.language == language,
    )
    result = await db.execute(stmt)
    cache = result.scalar_one_or_none()
    json_data = json.dumps(data, ensure_ascii=False)
    if cache:
        cache.data = json_data
        cache.updated_at = datetime.now(timezone.utc)
    else:
        cache = KeywordCache(
            cache_date=today,
            keyword=keyword,
            region=region,
            language=language,
            data=json_data,
        )
        db.add(cache)
    await db.flush()