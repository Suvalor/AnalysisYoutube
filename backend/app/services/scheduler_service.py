from __future__ import annotations

from datetime import date
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.crud.youtube import list_distinct_monitored_channels_for_org, upsert_channel, upsert_channel_history
from app.db.session import AsyncSessionLocal
from app.models.organization import Organization
from app.services.config_manager import resolve_integration_config
from app.services.quota_service import record_api_quota_usage
from app.services.youtube_service import fetch_channels_by_ids, parse_datetime


logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


async def sync_channels_daily_stats() -> None:
    """按组织分别同步监控池频道统计：使用各组织合并后的 YouTube API Key。"""
    async with AsyncSessionLocal() as session:
        org_ids = list((await session.execute(select(Organization.id))).scalars().all())
        if not org_ids:
            logger.info("定时任务：无组织，跳过。")
            return

        today = date.today()
        total_items = 0

        for oid in org_ids:
            channels = await list_distinct_monitored_channels_for_org(session, oid)
            if not channels:
                continue

            icfg = await resolve_integration_config(session, org_id=oid)
            if not (icfg.youtube_api_key or "").strip():
                logger.warning("定时任务：组织 org_id=%s 未配置 YouTube API Key，跳过。", oid)
                continue

            id_map = {c.yt_channel_id: c.id for c in channels}
            try:
                api_items, calls = await fetch_channels_by_ids(
                    list(id_map.keys()),
                    youtube_api_key=icfg.youtube_api_key,
                    return_call_count=True,
                )
            except Exception:
                logger.exception("定时任务：组织 org_id=%s 调用 YouTube API 失败", oid)
                continue

            await record_api_quota_usage(session, "channels", times=calls)

            for item in api_items:
                yt_channel_id = item.get("id")
                if not yt_channel_id:
                    continue
                snippet = item.get("snippet", {})
                statistics = item.get("statistics", {})

                channel = await upsert_channel(
                    session=session,
                    yt_channel_id=yt_channel_id,
                    title=snippet.get("title", ""),
                    description=snippet.get("description", ""),
                    thumbnail_url=(snippet.get("thumbnails", {}).get("high", {}) or {}).get("url"),
                    subscriber_count=int(statistics.get("subscriberCount", 0)),
                    total_views=int(statistics.get("viewCount", 0)),
                    video_count=int(statistics.get("videoCount", 0)),
                    published_at=parse_datetime(snippet.get("publishedAt")),
                )
                await upsert_channel_history(
                    session=session,
                    channel_id=channel.id,
                    record_date=today,
                    subscriber_count=channel.subscriber_count,
                    total_views=channel.total_views,
                    video_count=channel.video_count,
                )

            total_items += len(api_items)

        await session.commit()
        logger.info("定时任务：频道统计同步完成，本批 API 返回约 %s 条频道。", total_items)


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        sync_channels_daily_stats,
        trigger=IntervalTrigger(minutes=5),
        id="sync_channels_daily_stats",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("APScheduler 已启动。")


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler 已停止。")
