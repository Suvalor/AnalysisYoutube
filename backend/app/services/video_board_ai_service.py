"""视频看板 AI 建议服务：基于视频项目状态生成内容策略建议。"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.video_project import VideoProject
from app.crud.library import get_by_user
from app.models.library import ModelLibrary, PromptLibrary
from app.services.field_encryption import try_decrypt
from app.services.llm_openai_factory import (
    LLMClientFactory,
    LLMClientConfig,
    normalize_openai_base_url,
)

logger = logging.getLogger(__name__)


def _build_video_board_ai_rules() -> str:
    return (
        "你是一个资深的 YouTube 内容策略顾问。\n"
        "请根据提供的视频项目数据，生成内容策略建议。\n"
        "请严格只输出一个 JSON 对象，不要输出任何额外文字或 Markdown 代码块。\n"
        "JSON 必须包含以下键：\n"
        '  "content_gaps": "内容缺口分析 — 哪些主题/形式尚未覆盖",\n'
        '  "publishing_strategy": "发布策略建议 — 频率、时段、系列化",\n'
        '  "improvement_suggestions": "现有项目改进建议",\n'
        '  "trend_opportunities": "趋势机会 — 基于现有内容的延伸方向"\n'
        "所有字段为中文，每字段 100-300 字。"
    )


async def generate_video_board_ai_suggestion(
    session: AsyncSession,
    *,
    user_id: int,
    project_ids: list[int] | None = None,
    model_library_id: int | None = None,
    llm_model_name: str | None = None,
    agent_id: int | None = None,
) -> dict[str, Any]:
    """
    基于视频看板项目数据生成 AI 内容策略建议。
    入参：project_ids（可选，不传则取用户所有项目）、模型配置。
    出参：包含内容缺口、发布策略、改进建议等。
    """
    # 查询视频项目
    q = select(VideoProject).where(VideoProject.user_id == user_id)
    if project_ids:
        q = q.where(VideoProject.id.in_(project_ids))
    q = q.order_by(VideoProject.updated_at.desc()).limit(20)
    projects = list((await session.execute(q)).scalars().all())

    if not projects:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="暂无视频项目数据，请先创建项目")

    # 构建项目数据摘要
    project_summaries = []
    for p in projects:
        project_summaries.append({
            "id": p.id,
            "title": p.title or "",
            "status": p.status or "unknown",
            "due_date": str(p.due_date) if p.due_date else None,
            "script_id": p.script_id,
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

    rules = _build_video_board_ai_rules()
    system_prompt = (
        f"【智能体 / 分析任务说明】\n{agent_prepend}\n\n" if agent_prepend else ""
    ) + f"【输出格式与角色约束】\n{rules}"

    user_prompt = (
        f"请对以下 {len(project_summaries)} 个视频项目生成内容策略建议：\n\n"
        f"{json.dumps(project_summaries, ensure_ascii=False, indent=2)}"
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
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI 策略建议调用失败") from exc

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
        "suggestion": parsed,
        "_system_prompt": system_prompt,
        "_user_prompt": user_prompt,
        "_assistant_content": raw_content,
    }