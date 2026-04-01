from __future__ import annotations

import logging
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import oss2
from fastapi import HTTPException, status

from app.core.config import settings
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


def build_public_oss_url(object_key: str) -> str:
    endpoint = settings.aliyun_oss_endpoint
    bucket = settings.aliyun_oss_bucket_name
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return f"{endpoint.rstrip('/')}/{object_key}"
    return f"https://{bucket}.{endpoint}/{object_key}"


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


def upload_to_oss(final_file_path: str, file_type: str, original_name: str) -> str:
    required_values = [
        settings.aliyun_access_key_id,
        settings.aliyun_access_key_secret,
        settings.aliyun_oss_bucket_name,
        settings.aliyun_oss_endpoint,
    ]
    if not all(required_values):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="阿里云 OSS 配置不完整",
        )

    # OSS 初始化（可替换为 STS 临时凭证版本）
    auth = oss2.Auth(settings.aliyun_access_key_id, settings.aliyun_access_key_secret)
    bucket = oss2.Bucket(auth, f"https://{settings.aliyun_oss_endpoint}", settings.aliyun_oss_bucket_name)

    ext = Path(original_name).suffix
    object_key = f"materials/{file_type}/{datetime.utcnow():%Y/%m/%d}/{uuid4().hex}{ext}"
    try:
        bucket.put_object_from_file(object_key, final_file_path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"上传 OSS 失败: {exc}",
        ) from exc

    return build_public_oss_url(object_key)
