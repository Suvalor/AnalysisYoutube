"""
飞书云文档离线归档后台任务：占位实现导出链路，实际上传走 ObjectStorageBackend（与素材库相同策略）。
"""

from __future__ import annotations

import logging
import os
import tempfile

from fastapi import HTTPException

from app.crud.feishu_doc import get_feishu_doc
from app.db.session import AsyncSessionLocal
from app.services.config_manager import resolve_integration_config
from app.services.object_storage import get_write_backend

logger = logging.getLogger(__name__)

# 最小合法 PDF 字节（占位内容，未来替换为真实导出文件）
_MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


async def run_feishu_doc_archive_task(*, doc_id: int, org_id: int) -> None:
    """
    后台归档流程框架：
    1. 读取库内飞书 url
    2. （占位）未来：飞书 Open API 导出 / Playwright 渲染
    3. 使用当前组织合并配置选择写入后端，上传至对象存储
    4. 更新 archive_status / archive_file_url / archive_type
    """
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
            return

        tmp_path: str | None = None
        try:
            cfg = await resolve_integration_config(session, org_id=org_id)
            backend = get_write_backend(cfg)

            # 占位：此处应使用 feishu_url 拉取真实 PDF/Markdown（当前仅验证对象存储上传链路）
            logger.debug("归档占位导出 doc_id=%s url 长度=%s", doc_id, len(feishu_url))
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(_MINIMAL_PDF)
                tmp_path = tmp.name

            original_name = f"feishu_doc_{doc_id}.pdf"
            # file_type 归入 materials 路径下的独立子目录，便于区分业务
            stored = backend.upload_local_file(tmp_path, "feishu_archive", original_name)

            row.archive_status = "SUCCESS"
            row.archive_file_url = stored.public_url
            row.archive_type = "PDF"
            await session.commit()
        except HTTPException as exc:
            logger.exception("归档上传失败（HTTPException）doc_id=%s: %s", doc_id, exc.detail)
            row.archive_status = "FAILED"
            row.archive_file_url = None
            row.archive_type = None
            await session.commit()
        except Exception:
            logger.exception("归档任务异常 doc_id=%s org_id=%s", doc_id, org_id)
            row.archive_status = "FAILED"
            row.archive_file_url = None
            row.archive_type = None
            await session.commit()
        finally:
            if tmp_path and os.path.isfile(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
