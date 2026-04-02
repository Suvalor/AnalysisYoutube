"""在抓取 YouTube 基础数据后，用 LLM 丰富频道标签、擅长内容等字段。"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.library import get_by_user
from app.crud.youtube import create_youtube_channel_insight, update_channel_ai_insight
from app.models.library import ModelLibrary, PromptLibrary
from app.models.youtube import YouTubeChannel, YouTubeComment, YouTubeVideo
from app.services.field_encryption import try_decrypt
from app.services.config_manager import ResolvedIntegrationConfig, merge_integration_config
from app.services.youtube_ai_service import analyze_channel_ai_insight, build_channel_ai_messages

logger = logging.getLogger(__name__)


async def load_channel_ai_context(
    session: AsyncSession,
    channel: YouTubeChannel,
) -> tuple[list[str], list[str], list[str]]:
    """
    加载发给 LLM 的频道上下文：
    播放量 Top10 视频标题、合并视频标签、点赞 Top20 评论正文。
    """
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

    return top_video_titles, merged_tags, hot_comments


def _supported_model_values(ml: ModelLibrary) -> list[str]:
    raw = (ml.supported_models_json or "").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    out: list[str] = []
    for item in data:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
        elif isinstance(item, dict):
            v = str(item.get("value") or "").strip()
            if v:
                out.append(v)
    return out


def _ensure_llm_allowed_for_library(ml: ModelLibrary, llm_model_name: str) -> None:
    allowed = _supported_model_values(ml)
    if not allowed:
        return
    if llm_model_name.strip() not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"所选模型名不在该配置的支持列表中，可选：{', '.join(allowed[:20])}",
        )


async def enrich_youtube_channel_ai(
    session: AsyncSession,
    channel: YouTubeChannel,
    *,
    integration: ResolvedIntegrationConfig | None = None,
) -> bool:
    """
    基于频道简介、高播放量视频标题、视频标签与热门评论调用 LLM，写入 ai_tags / ai_expertise / ai_summary / ai_audience_age。
    integration 为合并后的用户+环境配置；未传时仅使用环境变量。
    """
    try:
        top_video_titles, merged_tags, hot_comments = await load_channel_ai_context(session, channel)
        messages = build_channel_ai_messages(
            channel_title=channel.title,
            channel_description=channel.description,
            top_video_titles=top_video_titles,
            merged_tags=merged_tags,
            hot_comments=hot_comments,
        )
        icfg = integration if integration is not None else merge_integration_config({})
        ai_result = await analyze_channel_ai_insight(messages, integration=icfg)

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
    except HTTPException:
        logger.warning(
            "频道 AI 丰富被拒绝 channel_id=%s yt_channel_id=%s（多为 LLM 配置或返回格式问题）",
            channel.id,
            channel.yt_channel_id,
        )
        return False
    except Exception:
        logger.exception("频道 AI 丰富失败 channel_id=%s yt_channel_id=%s", channel.id, channel.yt_channel_id)
        return False


async def run_channel_detail_ai_analysis(
    session: AsyncSession,
    *,
    channel: YouTubeChannel,
    user_id: int,
    model_library_id: int,
    llm_model_name: str,
    agent_id: int | None,
) -> dict[str, Any]:
    """
    博主详情页：使用配置中心模型（解密 Key + Base URL）与可选智能体 Prompt，调用 LLM 后写入频道字段并插入 insights 历史。
    """
    ml = await get_by_user(session, ModelLibrary, user_id, model_library_id)
    if ml is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型配置不存在或无权访问")

    api_key = try_decrypt(ml.api_key_encrypted)
    base_url = (ml.api_base_url or "").strip().rstrip("/")
    if not api_key or not base_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该模型配置缺少 API Key 或 Base URL，请在配置中心补全",
        )

    name = llm_model_name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="模型名不能为空")
    _ensure_llm_allowed_for_library(ml, name)

    agent_prepend: str | None = None
    if agent_id is not None:
        pl = await get_by_user(session, PromptLibrary, user_id, agent_id)
        if pl is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="智能体不存在或无权访问")
        agent_prepend = pl.content

    top_video_titles, merged_tags, hot_comments = await load_channel_ai_context(session, channel)
    messages = build_channel_ai_messages(
        channel_title=channel.title,
        channel_description=channel.description,
        top_video_titles=top_video_titles,
        merged_tags=merged_tags,
        hot_comments=hot_comments,
        agent_system_prepend=agent_prepend,
    )

    ai_result = await analyze_channel_ai_insight(
        messages,
        api_key=api_key,
        base_url=base_url,
        model=name,
    )

    tags = list(ai_result["tags"]) if isinstance(ai_result.get("tags"), list) else []
    expertise = str(ai_result.get("expertise") or "")
    age_group = str(ai_result.get("age_group") or "未标注")
    summary = str(ai_result.get("summary") or "")

    analyzed_at = datetime.now(timezone.utc)
    await update_channel_ai_insight(
        session,
        channel=channel,
        ai_tags=tags,
        ai_audience_age=age_group,
        ai_summary=summary,
        ai_expertise=expertise,
    )
    channel.ai_analyzed_at = analyzed_at
    channel.ai_source_model_library_id = model_library_id
    channel.ai_source_llm_model_name = name
    channel.ai_source_agent_id = agent_id
    await session.flush()

    await create_youtube_channel_insight(
        session,
        channel_id=channel.id,
        user_id=user_id,
        model_library_id=model_library_id,
        llm_model_name=name,
        agent_id=agent_id,
        ai_tags=tags,
        ai_expertise=expertise,
        ai_audience_age=age_group,
        ai_summary=summary,
    )

    return {
        "tags": tags,
        "expertise": expertise,
        "age_group": age_group,
        "summary": summary,
        "analyzed_at": analyzed_at,
        "model_library_id": model_library_id,
        "llm_model_name": name,
        "agent_id": agent_id,
    }


def channel_needs_ai_tag_fill(channel: YouTubeChannel) -> bool:
    """一键更新时：无标签则补全 AI 维度。"""
    tags = channel.ai_tags
    return not tags or (isinstance(tags, list) and len(tags) == 0)
