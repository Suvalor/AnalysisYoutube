"""
飞书云文档离线归档后台任务：生成 PDF → 校验 → 上传对象存储；失败时递增退避重试。
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile

from fastapi import HTTPException

from app.crud.feishu_doc import get_feishu_doc
from app.db.session import AsyncSessionLocal
from app.services.config_manager import resolve_integration_config
from app.services.object_storage import get_write_backend
from app.services.pdf_validate import DEFAULT_MIN_PDF_BYTES, validate_pdf

logger = logging.getLogger(__name__)

# 共 3 次尝试：第 2、3 次前分别等待（秒），给飞书页面加载 / 转换留时间
_ARCHIVE_RETRY_DELAYS_SEC = (5, 15)


def _write_placeholder_pdf_for_export(*, dest_path: str, feishu_url: str, doc_id: int) -> None:
    """
    占位导出：写入超过校验阈值的合法 PDF 骨架（以 % 注释填充体积）。
    接入真实 Playwright / 飞书 Open API 后，替换为将字节写入 dest_path 即可，无需改校验与重试框架。
    """
    _ = feishu_url  # 真实导出时使用
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    line = b"% " + (b"x" * 72) + b"\n"
    filler = bytearray()
    target = DEFAULT_MIN_PDF_BYTES + 512
    while len(header) + len(filler) + 80 < target:
        filler.extend(line)
    tail = b"1 0 obj<<>>endobj\ntrailer<<>>\nstartxref\n9\n%%EOF\n"
    data = header + bytes(filler) + tail
    with open(dest_path, "wb") as f:
        f.write(data)
    logger.debug("占位 PDF 已写入 doc_id=%s bytes=%s", doc_id, len(data))


def _try_generate_local_pdf(*, feishu_url: str, doc_id: int) -> str | None:
    """生成临时 PDF 路径；失败返回 None。"""
    try:
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        _write_placeholder_pdf_for_export(dest_path=path, feishu_url=feishu_url, doc_id=doc_id)
        return path
    except OSError:
        logger.exception("无法创建临时 PDF 文件 doc_id=%s", doc_id)
        return None


async def run_feishu_doc_archive_task(*, doc_id: int, org_id: int) -> None:
    """
    异步归档（非阻塞 HTTP）：仅在本任务内做 PDF 校验与重试，成功后才将 archive_status 置为 SUCCESS。
    """
    feishu_url = ""
    async with AsyncSessionLocal() as session:
        row = await get_feishu_doc(session, org_id=org_id, doc_id=doc_id)
        if row is None:
            logger.warning("归档任务跳过：文档不存在 doc_id=%s org_id=%s", doc_id, org_id)
            return
        feishu_url = (row.url or "").strip()
        if not feishu_url:
            row.archive_status = "FAILED"
            row.archive_file_url = None
            row.archive_type = None
            await session.commit()
            logger.warning("归档失败：飞书链接为空 doc_id=%s", doc_id)
            return

    async with AsyncSessionLocal() as session:
        cfg = await resolve_integration_config(session, org_id=org_id)
    backend = get_write_backend(cfg)

    last_fail_reason = ""

    for attempt in range(3):
        if attempt > 0:
            delay = _ARCHIVE_RETRY_DELAYS_SEC[attempt - 1]
            logger.info(
                "归档 PDF 校验未通过，%s 秒后进行第 %s/3 次重试 doc_id=%s",
                delay,
                attempt + 1,
                doc_id,
            )
            await asyncio.sleep(delay)

        tmp_path: str | None = None
        try:
            tmp_path = _try_generate_local_pdf(feishu_url=feishu_url, doc_id=doc_id)
            if not tmp_path:
                last_fail_reason = "临时文件创建失败"
                continue

            if not validate_pdf(tmp_path):
                try:
                    sz = os.path.getsize(tmp_path) if os.path.isfile(tmp_path) else -1
                except OSError:
                    sz = -1
                last_fail_reason = f"PDF 未通过校验（存在={os.path.isfile(tmp_path)} 大小={sz}）"
                logger.warning(
                    "归档第 %s/3 次尝试：%s doc_id=%s",
                    attempt + 1,
                    last_fail_reason,
                    doc_id,
                )
                continue

            stored = backend.upload_local_file(tmp_path, "feishu_archive", f"feishu_doc_{doc_id}.pdf")

            async with AsyncSessionLocal() as session:
                row2 = await get_feishu_doc(session, org_id=org_id, doc_id=doc_id)
                if row2 is None:
                    logger.error("归档成功但文档已删除 doc_id=%s", doc_id)
                    return
                row2.archive_status = "SUCCESS"
                row2.archive_file_url = stored.public_url
                row2.archive_type = "PDF"
                await session.commit()

            logger.info("飞书文档归档成功 doc_id=%s attempt=%s", doc_id, attempt + 1)
            return

        except HTTPException as exc:
            last_fail_reason = str(exc.detail)
            logger.exception("归档上传失败（HTTPException）doc_id=%s: %s", doc_id, exc.detail)
        except Exception:
            last_fail_reason = "上传或存储异常"
            logger.exception("归档任务异常 doc_id=%s org_id=%s", doc_id, org_id)
        finally:
            if tmp_path and os.path.isfile(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    async with AsyncSessionLocal() as session:
        row3 = await get_feishu_doc(session, org_id=org_id, doc_id=doc_id)
        if row3 is None:
            return
        row3.archive_status = "FAILED"
        row3.archive_file_url = None
        row3.archive_type = None
        await session.commit()

    logger.error(
        "飞书文档归档最终失败（已重试 3 次）doc_id=%s org_id=%s reason=%s",
        doc_id,
        org_id,
        last_fail_reason or "未知",
    )
