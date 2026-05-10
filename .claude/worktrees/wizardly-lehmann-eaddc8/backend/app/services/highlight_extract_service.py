"""Highlight extraction service -- uses LLM to identify key moments in a video."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.video_highlight import bulk_create_highlights, get_highlights_by_video
from app.models.youtube import YouTubeVideo
from app.services.field_encryption import try_decrypt
from app.services.llm_openai_factory import LLMClientFactory, LLMClientConfig

logger = logging.getLogger(__name__)


def _extract_highlights_json(raw_text: str) -> list[dict[str, Any]]:
    """Parse LLM response into a list of highlight dicts."""
    text = (raw_text or "").strip()
    if not text:
        return []

    # Strip markdown code blocks
    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        while lines and lines[-1].strip() == "":
            lines.pop()
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1:
            return []
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return []

    if not isinstance(data, list):
        return []

    highlights = []
    for item in data:
        if not isinstance(item, dict):
            continue
        start_sec = item.get("start_sec")
        end_sec = item.get("end_sec")
        if start_sec is None or end_sec is None:
            continue
        try:
            highlights.append({
                "start_sec": float(start_sec),
                "end_sec": float(end_sec),
                "score": float(item.get("score", 0.5)),
                "label": str(item.get("label", "")),
            })
        except (ValueError, TypeError):
            continue

    return highlights


def _model_has_api_key(ml: Any) -> bool:
    """Check whether a ModelLibrary row has a non-empty encrypted API key."""
    return bool(ml.api_key_encrypted and ml.api_key_encrypted.strip())


async def extract_video_highlights(
    db: AsyncSession,
    *,
    video: YouTubeVideo,
    user_id: int,
) -> list:
    """Use LLM to extract highlight segments from a video.

    Returns list of VideoHighlight objects created in the database.
    """
    from app.crud.library import list_by_user
    from app.models.library import ModelLibrary

    # Find a usable LLM model for this user
    rows = await list_by_user(db, ModelLibrary, user_id)
    ml = None
    for row in rows:
        if _model_has_api_key(row) and row.library_kind in ("llm", None, ""):
            ml = row
            break
    if ml is None:
        # Fallback: use first model with api_key
        for row in rows:
            if _model_has_api_key(row):
                ml = row
                break

    if ml is None:
        logger.warning("No LLM model available for user %d, cannot extract highlights", user_id)
        return []

    api_key = try_decrypt(ml.api_key_encrypted)
    base_url = (ml.api_base_url or "").strip().rstrip("/")
    if not api_key or not base_url:
        return []

    # Resolve model name
    supported: list[str] = []
    raw = (ml.supported_models_json or "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, str) and item.strip():
                        supported.append(item.strip())
                    elif isinstance(item, dict):
                        v = item.get("value", "")
                        if isinstance(v, str) and v.strip():
                            supported.append(v.strip())
        except json.JSONDecodeError:
            pass

    model_name = supported[0] if supported else "gpt-3.5-turbo"

    duration = video.duration_sec or 0
    system_prompt = (
        "你是一个专业的视频内容分析师。根据视频的元数据信息，识别视频中的精彩片段（高光时刻）。\n"
        "请输出一个 JSON 数组，每个元素包含：\n"
        '  "start_sec": 起始秒数（数字），\n'
        '  "end_sec": 结束秒数（数字），\n'
        '  "score": 重要性评分 0-1（数字），\n'
        '  "label": 片段描述（字符串，如"高潮转折""情绪爆发""关键信息"）\n\n'
        "规则：\n"
        "- 每个片段时长建议 3-15 秒\n"
        "- 片段不能超出视频总时长\n"
        "- 识别 3-8 个精彩片段\n"
        "- 只输出 JSON 数组，不要输出其他内容\n"
    )

    user_prompt = (
        f"【视频标题】{video.title}\n"
        f"【视频描述】{video.description or '无描述'}\n"
        f"【视频总时长】{duration} 秒\n"
        f"【播放量】{video.view_count}\n"
        f"【点赞数】{video.like_count}\n"
        f"【评论数】{video.comment_count}\n\n"
        "请分析并输出精彩片段列表。"
    )

    factory = LLMClientFactory()
    cfg = LLMClientConfig(api_key=api_key, base_url=base_url, model_name=model_name)

    try:
        content = await factory.chat_completions_content(
            cfg=cfg,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as exc:
        logger.warning("LLM call failed for highlight extraction: %s", exc)
        return []

    highlights_data = _extract_highlights_json(content or "")

    # Validate and clamp time ranges
    valid_highlights = []
    for h in highlights_data:
        start = max(0, h["start_sec"])
        end = min(h["end_sec"], float(duration)) if duration > 0 else h["end_sec"]
        if end <= start:
            continue
        valid_highlights.append({
            "start_sec": start,
            "end_sec": end,
            "score": h.get("score", 0.5),
            "label": h.get("label", ""),
        })

    if not valid_highlights:
        return []

    # Delete existing AI highlights for this video+user before creating new ones
    existing = await get_highlights_by_video(db, video.id, user_id)
    for hl in existing:
        if hl.source == "ai":
            await db.delete(hl)
    await db.flush()

    return await bulk_create_highlights(
        db,
        video_id=video.id,
        user_id=user_id,
        highlights=valid_highlights,
        source="ai",
    )
