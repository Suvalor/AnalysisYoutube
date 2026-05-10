"""
去水印插件：从「模型管理」与组织集成配置解析运行时 Inpainting 参数。

- OpenAI 兼容：model_libraries 中 library_kind=image_inpaint。
- 火山智能视觉 CV：组织集成 volc_cv_*（AccessKey/SecretKey/Region 等），走 Img2ImgInpainting。
- 提示词与视频参数：org_settings.payload_json 中的 watermark_inpaint_prompt、watermark_video_ai_max_frames。
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
class OpenAIInpaintSlice:
    """OpenAI 兼容 POST /v1/images/edits 所需参数。"""

    api_base_url: str
    api_key: str
    model_id: str
    prompt: str


@dataclass(frozen=True)
class VolcCvInpaintSlice:
    """火山 CV Img2ImgInpainting：AK/SK 来自组织集成或环境变量合并结果。"""

    access_key_id: str
    secret_access_key: str
    region: str
    host: str
    req_key: str


@dataclass(frozen=True)
class InpaintRuntimeConfig:
    """单次去水印请求：可同时具备火山 CV 与 OpenAI 兼容配置，执行时优先火山再 OpenAI。"""

    video_max_frames: int
    openai: OpenAIInpaintSlice | None
    volc_cv: VolcCvInpaintSlice | None

    def has_any_ai(self) -> bool:
        return self.openai is not None or self.volc_cv is not None


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
    watermark_model_id: int | None = None,
) -> InpaintRuntimeConfig | None:
    """
    解析运行时配置；若火山 CV 与 OpenAI 均未配置则返回 None，调用方回退本地 OpenCV。
    """
    icfg = await resolve_integration_config(session, org_id=org_id)
    prompt = (icfg.watermark_inpaint_prompt or "").strip() or DEFAULT_WATERMARK_INPAINT_PROMPT
    max_frames = icfg.watermark_video_ai_max_frames

    volc_cv: VolcCvInpaintSlice | None = None
    ak = (icfg.volc_cv_access_key_id or "").strip()
    sk = (icfg.volc_cv_secret_access_key or "").strip()
    if ak and sk:
        region = (icfg.volc_cv_region or "").strip() or "cn-north-1"
        host = (icfg.volc_cv_host or "").strip()
        req_key = (icfg.volc_cv_inpaint_req_key or "").strip() or "i2i_inpainting"
        volc_cv = VolcCvInpaintSlice(
            access_key_id=ak,
            secret_access_key=sk,
            region=region,
            host=host,
            req_key=req_key,
        )
    else:
        logger.debug("未配置 volc_cv_access_key_id/volc_cv_secret_access_key，跳过火山 CV Inpaint")

    openai_slice: OpenAIInpaintSlice | None = None
    if watermark_model_id is None:
        logger.info("未传入 watermark_model_id，跳过模型库 AI 去水印配置")
        row = None
    else:
        stmt = (
            select(ModelLibrary)
            .where(
                ModelLibrary.id == watermark_model_id,
                ModelLibrary.user_id == user_id,
                ModelLibrary.library_kind == MODEL_LIBRARY_KIND_IMAGE_INPAINT,
            )
            .limit(1)
        )
        row = (await session.execute(stmt)).scalar_one_or_none()
        if row is None:
            logger.warning(
                "watermark_model_id=%s 不存在、无权限或非 image_inpaint，跳过模型库 AI 去水印配置",
                watermark_model_id,
            )
    if row is not None:
        api_key = try_decrypt(row.api_key_encrypted)
        base = (row.api_base_url or "").strip().rstrip("/")
        if api_key and base:
            model_id = _first_supported_model_value(row.supported_models_json) or "dall-e-2"
            openai_slice = OpenAIInpaintSlice(
                api_base_url=base,
                api_key=api_key,
                model_id=model_id,
                prompt=prompt,
            )
        else:
            logger.warning("图像修复模型库 id=%s 缺少 API Key 或 Base URL，跳过 OpenAI 兼容 Inpaint", row.id)
    else:
        logger.info("未找到可用 image_inpaint 模型配置，跳过 OpenAI 兼容 Inpaint")

    if volc_cv is None and openai_slice is None:
        logger.info("未配置任何云端 Inpaint（火山 CV 与图像修复模型库均无）")
        return None

    return InpaintRuntimeConfig(
        video_max_frames=max_frames,
        openai=openai_slice,
        volc_cv=volc_cv,
    )
