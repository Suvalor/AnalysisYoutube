"""在抓取 YouTube 基础数据后，用 LLM 丰富频道标签、擅长内容等字段。"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.youtube import update_channel_ai_insight
from app.models.youtube import YouTubeChannel, YouTubeComment, YouTubeVideo
from app.services.youtube_ai_service import analyze_channel_ai_insight, build_channel_ai_messages

logger = logging.getLogger(__name__)


async def enrich_youtube_channel_ai(session: AsyncSession, channel: YouTubeChannel) -> bool:
    """
    基于频道简介、高播放量视频标题、视频标签与热门评论调用 LLM，写入 ai_tags / ai_expertise / ai_summary / ai_audience_age。
    失败时记录日志并返回 False，不向调用方抛异常（避免拖垮整批导入）。
    """
    try:
        top_videos_result = await session.execute(
            select(YouTubeVideo)
            .where(YouTubeVideo.channel_id == channel.id)
            .order_by(YouTubeVideo.view_count.desc())
            .limit(10)
        )
        top_videos = list(top_videos_result.scalars().all())
        top_video_titles = [x.title for x in top_videos if x.title]

        merged_tags: list[str] = []
        seen_tags: set[str] = set()
        for video in top_videos:
            for tag in video.tags or []:
                t = str(tag).strip()
                if not t or t in seen_tags:
                    continue
                seen_tags.add(t)
                merged_tags.append(t)
        merged_tags = merged_tags[:80]

        comments_result = await session.execute(
            select(YouTubeComment.text_original)
            .where(YouTubeComment.channel_id == channel.id)
            .order_by(YouTubeComment.like_count.desc(), YouTubeComment.created_at.desc())
            .limit(20)
        )
        hot_comments = [str(x[0]).strip() for x in comments_result.all() if x and str(x[0]).strip()]

        messages = build_channel_ai_messages(
            channel_title=channel.title,
            channel_description=channel.description,
            top_video_titles=top_video_titles,
            merged_tags=merged_tags,
            hot_comments=hot_comments,
        )
        ai_result = await analyze_channel_ai_insight(messages)

        tags = list(ai_result["tags"]) if isinstance(ai_result.get("tags"), list) else []
        await update_channel_ai_insight(
            session,
            channel=channel,
            ai_tags=tags,
            ai_audience_age=str(ai_result.get("age_group") or "未标注"),
            ai_summary=str(ai_result.get("summary") or ""),
            ai_expertise=str(ai_result.get("expertise") or ""),
        )
        await session.flush()
        return True
    except Exception:
        logger.exception("频道 AI 丰富失败 channel_id=%s yt_channel_id=%s", channel.id, channel.yt_channel_id)
        return False


def channel_needs_ai_tag_fill(channel: YouTubeChannel) -> bool:
    """一键更新时：无标签则补全 AI 维度。"""
    tags = channel.ai_tags
    return not tags or (isinstance(tags, list) and len(tags) == 0)
