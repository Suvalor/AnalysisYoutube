"""
本地 PDF 文件有效性校验：用于归档任务在「上传云存储 / 标记成功」前的结果检查。
"""

from __future__ import annotations

import os

# 飞书页转 PDF 若为空或几乎无内容，通常远小于该阈值（单位：字节）
DEFAULT_MIN_PDF_BYTES = 5 * 1024


def validate_pdf(file_path: str | None, *, min_bytes: int = DEFAULT_MIN_PDF_BYTES) -> bool:
    """
    校验路径是否存在、为文件、大小超过阈值，且文件头为 PDF 魔数 %PDF-。
    """
    if not file_path or not isinstance(file_path, str):
        return False
    if not os.path.isfile(file_path):
        return False
    try:
        size = os.path.getsize(file_path)
    except OSError:
        return False
    if size < min_bytes:
        return False
    try:
        with open(file_path, "rb") as f:
            head = f.read(5)
    except OSError:
        return False
    return head.startswith(b"%PDF-")
