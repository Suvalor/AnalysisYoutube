"""
去水印插件：从「模型管理」与组织集成配置解析运行时 Inpainting 参数。

- 图像修复模型：model_libraries 中 library_kind=image_inpaint，取当前用户最近更新的一条。
- 提示词与视频逐帧上限：org_settings.payload_json 中的 watermark_inpaint_prompt、watermark_video_ai_max_frames。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.library import ModelLibrary
from app.services.config_manager import DEFAULT_WATERMARK_INPAINT_PROMPT, resolve_integration_config
from app.services.field_encryption import try_decrypt

logger = logging.getLogger(__name__)

MODEL_LIBRARY_KIND_CHAT = "chat"
MODEL_LIBRARY_KIND_IMAGE_INPAINT = "image_inpaint"


@dataclass(frozen=True)
class InpaintRuntimeConfig:
    """单次去水印请求使用的 AI 修复参数（OpenAI 兼容 POST /v1/images/edits）。"""

    api_base_url: str
    api_key: str
    model_id: str
    prompt: str
    video_max_frames: int


def _first_supported_model_value(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list) or not data:
        return None
    first = data[0]
    if isinstance(first, dict):
        v = str(first.get("value") or "").strip()
        return v or None
    if isinstance(first, str) and first.strip():
        return first.strip()
    return None


async def resolve_inpaint_runtime_config(
    session: AsyncSession,
    *,
    user_id: int,
    org_id: int | None,
) -> InpaintRuntimeConfig | None:
    """
    无有效「图像修复」模型库条目时返回 None，调用方应记录日志并回退本地算法。
    """
    icfg = await resolve_integration_config(session, org_id=org_id)
    prompt = (icfg.watermark_inpaint_prompt or "").strip() or DEFAULT_WATERMARK_INPAINT_PROMPT

    max_frames = icfg.watermark_video_ai_max_frames

    stmt = (
        select(ModelLibrary)
        .where(
            ModelLibrary.user_id == user_id,
            ModelLibrary.library_kind == MODEL_LIBRARY_KIND_IMAGE_INPAINT,
        )
        .order_by(ModelLibrary.updated_at.desc())
        .limit(1)
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        logger.info("未找到配置的 AI 图像模型（model_libraries.library_kind=image_inpaint），去水印将使用本地算法")
        return None

    api_key = try_decrypt(row.api_key_encrypted)
    if not api_key:
        logger.warning("图像修复模型库 id=%s 未设置有效 API Key，去水印将使用本地算法", row.id)
        return None

    base = (row.api_base_url or "").strip().rstrip("/")
    if not base:
        return None

    model_id = _first_supported_model_value(row.supported_models_json) or "dall-e-2"

    return InpaintRuntimeConfig(
        api_base_url=base,
        api_key=api_key,
        model_id=model_id,
        prompt=prompt,
        video_max_frames=max_frames,
    )
