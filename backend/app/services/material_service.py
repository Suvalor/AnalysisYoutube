from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi import HTTPException, status
import numpy as np
from PIL import Image

if TYPE_CHECKING:
    from app.services.watermark_inpaint_config import InpaintRuntimeConfig

logger = logging.getLogger(__name__)

_PROCESS_INFO_SKIP_ENGINE = "素材上传成功，但 AI 去水印处理失败，已上传原文件"


def process_watermark_removal_best_effort(
    temp_filepath: str,
    file_type: str,
    *,
    inpaint_config: InpaintRuntimeConfig | None = None,
) -> tuple[str, str]:
    """
    去水印（插件、尽力而为）。

    - 永不抛出 HTTPException；失败时始终返回原始临时文件路径，保证主流程可继续上传。
    - 返回 (本地最终路径, process_info)，供接口写入响应。
    """
    input_path = Path(temp_filepath)
    output_path = input_path.with_name(f"{input_path.stem}_clean{input_path.suffix}")

    if inpaint_config is None or not inpaint_config.has_any_ai():
        logger.warning("未命中可用 AI 去水印配置，跳过处理并保留原文件 path=%s", temp_filepath)
        return temp_filepath, "素材上传成功，但未配置可用 AI 去水印模型，已上传原文件"

    if file_type != "image":
        logger.info("当前文件类型尚未支持纯 AI 去水印，跳过处理 file_type=%s", file_type)
        return temp_filepath, "素材上传成功；当前类型暂不支持 AI 去水印，已上传原文件"

    try:
        from app.services.watermark_inpaint_client import inpaint_bgr_with_runtime_config_or_none
    except Exception:
        logger.exception("AI 去水印模块加载失败，已保留原文件 path=%s", temp_filepath)
        return temp_filepath, _PROCESS_INFO_SKIP_ENGINE

    try:
        with Image.open(input_path) as pil_img:
            rgb = pil_img.convert("RGB")
            image_bgr = np.array(rgb)[:, :, ::-1].copy()
        h, w = image_bgr.shape[:2]
        # 纯 AI 路径下没有本地 OCR，这里使用全图 mask 交由模型完成去水印。
        mask_u8 = np.full((h, w), 255, dtype=np.uint8)
        out_bgr = inpaint_bgr_with_runtime_config_or_none(image_bgr, mask_u8, inpaint_config)
        if out_bgr is None:
            logger.error("AI 去水印失败，保留原图 path=%s", temp_filepath)
            return temp_filepath, _PROCESS_INFO_SKIP_ENGINE
        out_rgb = out_bgr[:, :, ::-1]
        Image.fromarray(out_rgb).save(output_path)
        return str(output_path), "AI 去水印处理已完成"
    except Exception:
        logger.exception("AI 去水印处理异常，已保留原文件 path=%s", temp_filepath)
        return temp_filepath, _PROCESS_INFO_SKIP_ENGINE


def infer_file_type(content_type: str | None) -> str:
    if content_type and content_type.startswith("image/"):
        return "image"
    if content_type and content_type.startswith("video/"):
        return "video"
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持图片或视频文件")


def infer_asset_library_file_type(content_type: str | None) -> str:
    """素材库（/api/assets/upload）支持图片、视频、音频。"""
    if content_type and content_type.startswith("image/"):
        return "image"
    if content_type and content_type.startswith("video/"):
        return "video"
    if content_type and content_type.startswith("audio/"):
        return "audio"
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持图片、视频或音频文件")


def infer_asset_library_file_type_loose(content_type: str | None, filename: str) -> str:
    """预签名直传：优先 MIME，其次根据扩展名推断。"""
    if content_type and content_type.strip():
        try:
            return infer_asset_library_file_type(content_type)
        except HTTPException:
            pass
    ext = Path(filename or "").suffix.lower()
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".ico"}:
        return "image"
    if ext in {".mp4", ".webm", ".mov", ".m4v", ".avi", ".mkv"}:
        return "video"
    if ext in {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}:
        return "audio"
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="无法识别文件类型，请提供正确的 Content-Type 或使用常见图片/视频/音频扩展名",
    )


def save_upload_to_temp(upload_filename: str, binary_content: bytes) -> tuple[str, str]:
    suffix = Path(upload_filename).suffix or ""
    tmp_dir = tempfile.mkdtemp(prefix="material_upload_")
    tmp_path = os.path.join(tmp_dir, f"{uuid4().hex}{suffix}")
    with open(tmp_path, "wb") as f:
        f.write(binary_content)
    return tmp_dir, tmp_path


def remove_temp_dir(tmp_dir: str) -> None:
    if tmp_dir and os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir, ignore_errors=True)
