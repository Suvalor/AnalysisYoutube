from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from app.services.watermark_remover import auto_remove_text_watermark
from app.services.video_watermark_remover import auto_remove_video_watermark


logger = logging.getLogger(__name__)


def process_watermark_removal(temp_filepath: str, file_type: str) -> str:
    """
    去水印处理函数。
    - 当前仅对图片执行 OCR + inpaint 去水印。
    - 视频等非图片类型直接返回原路径。
    """
    input_path = Path(temp_filepath)
    output_path = input_path.with_name(f"{input_path.stem}_clean{input_path.suffix}")

    if file_type == "image":
        ok = auto_remove_text_watermark(str(input_path), str(output_path))
    elif file_type == "video":
        ok = auto_remove_video_watermark(str(input_path), str(output_path))
    else:
        logger.info("当前文件类型不支持去水印，跳过处理，file_type=%s", file_type)
        return temp_filepath

    if not ok:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="去水印处理失败",
        )
    return str(output_path)


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
