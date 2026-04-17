"""竞对洞察 AI 服务：基于频道数据生成竞争格局分析。"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.youtube import YouTubeChannel, YouTubeVideo
from app.crud.library import get_by_user
from app.models.library import ModelLibrary, PromptLibrary
from app.services.field_encryption import try_decrypt
from app.services.llm_openai_factory import (
    LLMClientFactory,
    LLMClientConfig,
    normalize_openai_base_url,
)

logger = logging.getLogger(__name__)


def _build_competitor_insight_rules() -> str:
    return (
        "你是一个资深的 YouTube 竞争分析师。\n"
        "请根据提供的多个频道数据，生成竞争格局分析。\n"
        "请严格只输出一个 JSON 对象，不要输出任何额外文字或 Markdown 代码块。\n"
        "JSON 必须包含以下键：\n"
        '  "positioning_diff": "各频道定位差异分析",\n'
        '  "content_strategy_diff": "内容策略差异分析",\n'
        '  "audience_overlap": "受众重叠度分析",\n'
        '  "competitive_summary": "竞争格局总结",\n'
        '  "actionable_advice": "针对用户的可操作建议"\n'
        "所有字段为中文，每字段 100-300 字。"
    )


async def generate_competitor_ai_insight(
    session: AsyncSession,
    *,
    user_id: int,
    channel_ids: list[int],
    model_library_id: int | None = None,
    llm_model_name: str | None = None,
    agent_id: int | None = None,
) -> dict[str, Any]:
    """
    基于频道数据生成 AI 竞争分析。
    入参：channel_ids（2-3个频道ID）、模型配置。
    出参：包含定位差异、内容策略差异、受众重叠度等分析结果。
    """
    # 查询频道数据
    channels_q = select(YouTubeChannel).where(YouTubeChannel.id.in_(channel_ids))
    channels = list((await session.execute(channels_q)).scalars().all())
    if len(channels) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="至少需要 2 个频道才能进行竞对分析")

    # 构建频道数据摘要
    channel_summaries = []
    for ch in channels:
        # 获取频道近期视频标题
        videos_q = (
            select(YouTubeVideo.title)
            .where(YouTubeVideo.channel_id == ch.id)
            .order_by(YouTubeVideo.view_count.desc())
            .limit(10)
        )
        video_titles = list((await session.execute(videos_q)).scalars().all())
        channel_summaries.append({
            "title": ch.title,
            "subscriber_count": ch.subscriber_count,
            "total_views": ch.total_views,
            "video_count": ch.video_count,
            "ai_tags": ch.ai_tags or [],
            "ai_expertise": ch.ai_expertise or "",
            "top_video_titles": video_titles,
        })

    # 解析 LLM 配置
    if not model_library_id or not llm_model_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择 AI 模型配置")

    ml = await get_by_user(session, ModelLibrary, user_id, model_library_id)
    if ml is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型配置不存在")

    api_key = try_decrypt(ml.api_key_encrypted)
    base_url = normalize_openai_base_url((ml.api_base_url or "").strip())
    if not api_key or not base_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="模型配置缺少 API Key 或 Base URL")

    # 构建智能体系统提示词
    agent_prepend = ""
    if agent_id:
        prompt = await get_by_user(session, PromptLibrary, user_id, agent_id)
        if prompt:
            agent_prepend = prompt.content or ""

    rules = _build_competitor_insight_rules()
    system_prompt = (
        f"【智能体 / 分析任务说明】\n{agent_prepend}\n\n" if agent_prepend else ""
    ) + f"【输出格式与角色约束】\n{rules}"

    user_prompt = (
        f"请对以下 {len(channels)} 个 YouTube 频道进行竞争格局分析：\n\n"
        f"{json.dumps(channel_summaries, ensure_ascii=False, indent=2)}"
    )

    factory = LLMClientFactory()
    cfg = LLMClientConfig(api_key=api_key, base_url=base_url, model_name=llm_model_name)

    try:
        raw_content = await factory.chat_completions_content(
            cfg=cfg,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI 竞对分析调用失败") from exc

    # 解析结果
    try:
        text = (raw_content or "").strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            while lines and lines[-1].strip() == "":
                lines.pop()
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            parsed = json.loads(text[start:end + 1])
        else:
            parsed = json.loads(text)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI 返回格式异常，请重试")

    return {
        "insight": parsed,
        "_system_prompt": system_prompt,
        "_user_prompt": user_prompt,
        "_assistant_content": raw_content,
    }
