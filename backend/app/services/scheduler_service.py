from __future__ import annotations

from datetime import date
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.crud.youtube import list_distinct_monitored_channels, upsert_channel, upsert_channel_history
from app.db.session import AsyncSessionLocal
from app.services.youtube_service import fetch_channels_by_ids, parse_datetime


logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


async def sync_channels_daily_stats() -> None:
    """同步监控池频道的最新统计，并写入按天历史。"""
    async with AsyncSessionLocal() as session:
        channels = await list_distinct_monitored_channels(session)
        if not channels:
            logger.info("定时任务：当前没有监控频道，跳过同步。")
            return

        id_map = {c.yt_channel_id: c.id for c in channels}
        api_items = await fetch_channels_by_ids(list(id_map.keys()))
        today = date.today()

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

        await session.commit()
        logger.info("定时任务：频道统计同步完成，共 %s 个频道。", len(api_items))


def start_scheduler() -> None:
    if scheduler.running:
        return
    # 本地测试使用每 5 分钟执行一次；生产可改为 CronTrigger(hour=2, minute=0)
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

