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
from app.models.user import User, UserRole
from app.models.youtube import YouTubeChannel, YouTubeComment, YouTubeVideo
from app.services.field_encryption import try_decrypt
from app.services.llm_openai_factory import (
    LLMClientConfig,
    LLMClientFactory,
    normalize_base_url,
)
from app.services.youtube_ai_service import (
    _extract_json_object,
    _parse_insight_result,
    analyze_channel_info_sync,
    build_channel_ai_messages,
)
from app.services.rate_limit_service import check_quota, increment_usage

logger = logging.getLogger(__name__)


async def _try_consume_background_llm_quota(session: AsyncSession, user_id: int) -> bool:
    """后台 AI 补全前消费一次 LLM 配额；超限时跳过 AI，不影响基础数据入库。"""
    user = await session.get(User, user_id)
    if user is None:
        logger.warning("后台 LLM 配额检查失败：用户不存在 user_id=%s", user_id)
        return False

    subscription_quotas = None
    if user.role == UserRole.SUBSCRIBER:
        from app.crud.subscription_crud import get_active_user_subscription

        sub = await get_active_user_subscription(session, user_id)
        if sub and sub.plan:
            subscription_quotas = sub.plan.quotas_json

    allowed, used, limit = await check_quota(
        session,
        user_id=user_id,
        role=user.role,
        api_type="llm_api",
        subscription_quotas=subscription_quotas,
    )
    if not allowed:
        logger.warning("后台 LLM 配额已用尽：user_id=%s used=%s limit=%s", user_id, used, limit)
        return False

    await increment_usage(
        session,
        user_id=user_id,
        role=user.role,
        api_type="llm_api",
    )
    await session.commit()
    return True


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


async def _resolve_default_llm_credentials(
    session: AsyncSession,
    user_id: int,
) -> tuple[str, str, str, str] | None:
    """
    查找用户默认 chat 模型库配置，返回 (api_key, base_url, model_name, protocol)。
    无可用配置时返回 None。
    """
    ml_q = (
        select(ModelLibrary)
        .where(ModelLibrary.user_id == user_id, ModelLibrary.library_kind == "chat")
        .order_by(ModelLibrary.id.asc())
        .limit(1)
    )
    ml = (await session.execute(ml_q)).scalar_one_or_none()
    if ml is None:
        return None

    api_key = try_decrypt(ml.api_key_encrypted)
    base_url = (ml.api_base_url or "").strip().rstrip("/")
    protocol = (ml.protocol or "anthropic").strip()

    # 提取第一个支持的模型名
    raw = (ml.supported_models_json or "").strip()
    model_name = ""
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("value"):
                        model_name = str(item["value"]).strip()
                        break
                    elif isinstance(item, str) and item.strip():
                        model_name = item.strip()
                        break
        except json.JSONDecodeError:
            pass

    if not api_key or not base_url or not model_name:
        return None

    return api_key, base_url, model_name, protocol


async def enrich_youtube_channel_ai(
    session: AsyncSession,
    channel: YouTubeChannel,
    **_kwargs: Any,
) -> bool:
    """
    基于频道简介、高播放量视频标题、视频标签与热门评论调用 LLM，写入 ai_tags / ai_expertise / ai_summary / ai_audience_age。
    此路径为遗留入口，无 ModelLibrary 凭据，直接降级返回 False。
    前台显式选择模型的场景请使用 run_channel_detail_ai_analysis。
    """
    logger.warning(
        "enrich_youtube_channel_ai 为遗留入口，已降级返回 False（channel_id=%s）",
        channel.id,
    )
    return False


async def enrich_youtube_channel_ai_sync(
    session: AsyncSession,
    channel: YouTubeChannel,
    *,
    user_id: int,
    **_kwargs: Any,
) -> bool:
    """
    后台专用：非流式打标签（必须 stream=False），并具备强降级容错。

    - analyze_channel_info_sync 内部保证：任何异常都不会抛出
    - 若 AI 失败：tags 为空数组仍可成功入库基础统计数据
    - 无可用 LLM 凭据时直接降级返回 False
    """
    creds = await _resolve_default_llm_credentials(session, user_id)
    if creds is None:
        logger.warning("enrich_youtube_channel_ai_sync：无可用 LLM 配置，降级跳过（user_id=%s）", user_id)
        return False
    if not await _try_consume_background_llm_quota(session, user_id):
        return False

    api_key, base_url, model_name, protocol = creds
    top_video_titles, merged_tags, hot_comments = await load_channel_ai_context(session, channel)
    ai = await analyze_channel_info_sync(
        channel_title=channel.title,
        channel_description=channel.description,
        top_video_titles=top_video_titles,
        merged_tags=merged_tags,
        hot_comments=hot_comments,
        api_key=api_key,
        base_url=base_url,
        model=model_name,
        protocol=protocol,
    )
    tags = ai.get("tags") if isinstance(ai.get("tags"), list) else []
    expertise = str(ai.get("expertise") or "").strip()

    await update_channel_ai_insight(
        session,
        channel=channel,
        ai_tags=list(tags)[:5],
        ai_audience_age="未标注",
        ai_summary="",
        ai_expertise=expertise,
    )
    await session.flush()
    return len(tags) > 0


async def enrich_youtube_channel_info_ai_sync(
    session: AsyncSession,
    channel: YouTubeChannel,
    *,
    user_id: int,
    **_kwargs: Any,
) -> bool:
    """
    后台专用：只基于 channel.title + channel.description 做"轻量 JSON 打标签"。

    成本与性能目标：
    - 不读取数据库的 Top10 视频/Top评论/标签合并上下文
    - 直接传入空上下文数组给 analyze_channel_info_sync
    - AI 失败不抛异常，只写入 tags=[] + expertise=""（基础统计不受影响）
    - 无可用 LLM 凭据时直接降级返回 False
    """
    creds = await _resolve_default_llm_credentials(session, user_id)
    if creds is None:
        logger.warning("enrich_youtube_channel_info_ai_sync：无可用 LLM 配置，降级跳过（user_id=%s）", user_id)
        return False
    if not await _try_consume_background_llm_quota(session, user_id):
        return False

    api_key, base_url, model_name, protocol = creds
    ai = await analyze_channel_info_sync(
        channel_title=channel.title,
        channel_description=channel.description,
        top_video_titles=[],
        merged_tags=[],
        hot_comments=[],
        api_key=api_key,
        base_url=base_url,
        model=model_name,
        protocol=protocol,
    )
    tags = ai.get("tags") if isinstance(ai.get("tags"), list) else []
    expertise = str(ai.get("expertise") or "").strip()

    await update_channel_ai_insight(
        session,
        channel=channel,
        ai_tags=list(tags)[:5],
        ai_audience_age="未标注",
        ai_summary="",
        ai_expertise=expertise,
    )
    await session.flush()
    return len(tags) > 0


async def run_channel_detail_ai_analysis(
    session: AsyncSession,
    *,
    channel: YouTubeChannel,
    user_id: int,
    org_id: int,
    model_library_id: int,
    llm_model_name: str,
    agent_id: int | None,
) -> dict[str, Any]:
    """
    博主详情页：使用配置中心模型（解密 Key + Base URL）与可选智能体 Prompt，调用 LLM 后写入频道字段并插入 insights 历史。
    """
    # 第1步：从配置中心获取用户指定的模型库配置（API Key、Base URL 等）
    ml = await get_by_user(session, ModelLibrary, user_id, model_library_id)
    if ml is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型配置不存在或无权访问")

    # 第2步：解密 API Key 并校验 Base URL 是否存在
    api_key = try_decrypt(ml.api_key_encrypted)
    base_url = (ml.api_base_url or "").strip().rstrip("/")
    if not api_key or not base_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该模型配置缺少 API Key 或 Base URL，请在配置中心补全",
        )

    # 第3步：校验用户指定的模型名是否在该模型库的支持列表中
    name = llm_model_name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="模型名不能为空")
    _ensure_llm_allowed_for_library(ml, name)

    # 第4步：若指定了智能体（agent_id），则加载智能体的 Prompt 内容作为系统提示词前缀
    agent_prepend: str | None = None
    if agent_id is not None:
        pl = await get_by_user(session, PromptLibrary, user_id, agent_id)
        if pl is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="智能体不存在或无权访问")
        agent_prepend = pl.content

    # 第5步：加载频道上下文数据——播放量 Top10 视频标题、合并视频标签、点赞 Top20 评论
    top_video_titles, merged_tags, hot_comments = await load_channel_ai_context(session, channel)

    # 第6步：将频道信息与上下文组装成 LLM 对话消息列表（system + user）
    messages = build_channel_ai_messages(
        channel_title=channel.title,
        channel_description=channel.description,
        top_video_titles=top_video_titles,
        merged_tags=merged_tags,
        hot_comments=hot_comments,
        agent_system_prepend=agent_prepend,
    )

    # 第7步：构建 LLM 客户端配置（API Key、Base URL、模型名、协议）
    factory = LLMClientFactory()
    protocol = (ml.protocol or "anthropic").strip()
    cfg = LLMClientConfig(
        api_key=api_key,
        base_url=normalize_base_url(base_url),
        model_name=name,
        protocol=protocol,
    )

    # 第8步：从消息列表中提取 system_prompt 和 user_prompt，用于调用 LLM
    system_prompt = ""
    user_prompt = ""
    for msg in messages:
        role = str(msg.get("role") or "").strip()
        content = str(msg.get("content") or "").strip()
        if role == "system":
            system_prompt = content
        elif role == "user":
            user_prompt = content

    # 第9步：调用 LLM 获取 AI 分析结果（非流式），失败则返回 502
    try:
        raw_content = await factory.chat_completions_content(
            cfg=cfg,
            temperature=0.35,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI 分析调用失败，请稍后重试",
        ) from exc

    # 第10步：从 LLM 原始返回文本中提取 JSON 对象，格式异常则返回 502
    try:
        parsed = _extract_json_object(raw_content)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI 返回格式异常，请重试或调整提示词",
        ) from exc

    # 第11步：解析 JSON 为结构化字段（tags、expertise、age_group、summary）
    ai_result = _parse_insight_result(parsed)

    # 第12步：提取各字段并设置默认值
    tags = list(ai_result["tags"]) if isinstance(ai_result.get("tags"), list) else []
    expertise = str(ai_result.get("expertise") or "")
    age_group = str(ai_result.get("age_group") or "未标注")
    summary = str(ai_result.get("summary") or "")

    # 第13步：将 AI 分析结果写入频道主表（ai_tags / ai_audience_age / ai_summary / ai_expertise）
    analyzed_at = datetime.now(timezone.utc)
    await update_channel_ai_insight(
        session,
        channel=channel,
        ai_tags=tags,
        ai_audience_age=age_group,
        ai_summary=summary,
        ai_expertise=expertise,
    )
    # 第14步：记录本次分析使用的模型、智能体等元信息到频道主表
    channel.ai_analyzed_at = analyzed_at
    channel.ai_source_model_library_id = model_library_id
    channel.ai_source_llm_model_name = name
    channel.ai_source_agent_id = agent_id
    await session.flush()

    # 第15步：插入一条 insight 历史记录，用于追踪每次 AI 分析的完整快照
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

    # 第16步：返回结构化分析结果给前端
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
