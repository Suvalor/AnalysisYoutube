from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status

# 注意：禁止在此文件顶层 import paddle / watermark_*，避免未请求去水印时也加载 OCR 栈。


logger = logging.getLogger(__name__)

# 与产品文案对齐：环境/初始化类问题
_PROCESS_INFO_SKIP_ENGINE = "素材上传成功，但去水印处理因环境组件初始化失败而跳过"


def process_watermark_removal_best_effort(temp_filepath: str, file_type: str) -> tuple[str, str]:
    """
    去水印（插件、尽力而为）。

    - 永不抛出 HTTPException；失败时始终返回原始临时文件路径，保证主流程可继续上传。
    - 返回 (本地最终路径, process_info)，供接口写入响应。
    """
    input_path = Path(temp_filepath)
    output_path = input_path.with_name(f"{input_path.stem}_clean{input_path.suffix}")

    try:
        from app.services.watermark_remover import auto_remove_text_watermark
        from app.services.video_watermark_remover import auto_remove_video_watermark
    except Exception:
        logger.exception(
            "去水印模块加载失败（通常为 Paddle/OpenCV/numpy 环境冲突），已跳过去水印并保留原文件 path=%s",
            temp_filepath,
        )
        return temp_filepath, _PROCESS_INFO_SKIP_ENGINE

    try:
        if file_type == "image":
            ok, reason = auto_remove_text_watermark(str(input_path), str(output_path))
        elif file_type == "video":
            ok, reason = auto_remove_video_watermark(str(input_path), str(output_path))
        else:
            logger.info("当前文件类型不支持去水印，跳过插件逻辑，file_type=%s", file_type)
            return temp_filepath, "素材上传成功；当前类型不支持去水印，已上传原文件"

        if ok:
            return str(output_path), "去水印处理已完成"

        logger.error("去水印未通过 file_type=%s input=%s reason=%s", file_type, temp_filepath, reason)
        detail = (reason or "未知原因").strip()
        return temp_filepath, f"素材上传成功，但去水印处理未成功（{detail}），已上传原文件"

    except Exception:
        logger.exception("去水印处理发生未捕获异常，已降级为原文件上传，path=%s", temp_filepath)
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
