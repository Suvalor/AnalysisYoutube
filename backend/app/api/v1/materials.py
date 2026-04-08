from datetime import datetime, time

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import or_, select

from app.api.deps import CurrentUserDep, DBSessionDep
from app.constants.asset_source import (
    ALLOWED_ASSET_SOURCES,
    ASSET_SOURCE_INSPIRATION,
    ASSET_SOURCE_SOP,
)
from app.models.library import AssetLibrary
from app.schemas.materials import (
    MaterialAccessUrlResponse,
    MaterialRead,
    MaterialTypeEnum,
    MaterialUploadResponse,
)
from app.services.material_service import (
    infer_file_type,
    process_watermark_removal_best_effort,
    remove_temp_dir,
    save_upload_to_temp,
)
from app.services.watermark_inpaint_config import resolve_inpaint_runtime_config
from app.services.asset_access_service import library_row_access_url
from app.services.config_manager import resolve_integration_config
from app.services.object_storage import get_write_backend, material_access_url


router = APIRouter()


def _normalize_material_source(raw: str) -> str:
    s = (raw or ASSET_SOURCE_INSPIRATION).strip().upper()
    return s if s in ALLOWED_ASSET_SOURCES else ASSET_SOURCE_INSPIRATION


@router.get("", response_model=list[MaterialRead])
async def list_materials(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    type: MaterialTypeEnum | None = Query(default=None, description="文件类型：image/video"),
    start_date: str | None = Query(default=None, description="开始日期，格式 YYYY-MM-DD"),
    end_date: str | None = Query(default=None, description="结束日期，格式 YYYY-MM-DD"),
) -> list[MaterialRead]:
    # 排除 SOP 专用落库行；其余（MANUAL / INSPIRATION / 历史 NULL）供通用素材列表
    query = select(AssetLibrary).where(
        AssetLibrary.user_id == current_user.id,
        or_(AssetLibrary.source != ASSET_SOURCE_SOP, AssetLibrary.source.is_(None)),
    )
    if type is not None:
        query = query.where(AssetLibrary.file_type == type.value)

    if start_date:
        try:
            dt_start = datetime.combine(datetime.strptime(start_date, "%Y-%m-%d").date(), time.min)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="start_date 格式必须为 YYYY-MM-DD") from exc
        query = query.where(AssetLibrary.created_at >= dt_start)
    if end_date:
        try:
            dt_end = datetime.combine(datetime.strptime(end_date, "%Y-%m-%d").date(), time.max)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="end_date 格式必须为 YYYY-MM-DD") from exc
        query = query.where(AssetLibrary.created_at <= dt_end)

    query = query.order_by(AssetLibrary.id.desc())
    rows = (await db.execute(query)).scalars().all()
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    return [
        MaterialRead.model_validate(x).model_copy(
            update={"access_url": library_row_access_url(x, icfg)},
        )
        for x in rows
    ]


@router.get("/{material_id}/access-url", response_model=MaterialAccessUrlResponse)
async def get_material_access_url(
    material_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    expires: int = Query(default=3600, ge=60, le=86400, description="签名 URL 有效秒数"),
) -> MaterialAccessUrlResponse:
    """
    根据该行素材的 storage_platform / storage_object_key 生成访问链接。
    无 object_key 的历史数据返回 file_url（public_fallback）。
    """
    result = await db.execute(
        select(AssetLibrary).where(
            AssetLibrary.id == material_id,
            AssetLibrary.user_id == current_user.id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="素材不存在或无权访问")

    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    url, mode = material_access_url(
        storage_platform=row.storage_platform,
        storage_object_key=row.storage_object_key,
        file_url_fallback=row.file_url,
        expires_seconds=expires,
        cfg=icfg,
    )
    return MaterialAccessUrlResponse(
        url=url,
        mode=mode,
        expires_in=expires if mode == "presigned" else None,
    )


@router.post("/upload", response_model=MaterialUploadResponse)
async def upload_material(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    file: UploadFile = File(...),
    remove_watermark: bool = Form(default=False),
    watermark_model_id: int | None = Form(default=None),
    source: str = Form(default=ASSET_SOURCE_INSPIRATION),
) -> MaterialUploadResponse:
    raw_bytes = await file.read()
    file_size = len(raw_bytes)
    file_type = infer_file_type(file.content_type)
    src = _normalize_material_source(source)

    tmp_dir = ""
    try:
        tmp_dir, temp_path = save_upload_to_temp(file.filename or "upload.bin", raw_bytes)
        final_path = temp_path
        process_info = "未启用去水印"
        if remove_watermark:
            inpaint_cfg = await resolve_inpaint_runtime_config(
                db,
                user_id=current_user.id,
                org_id=current_user.org_id,
                watermark_model_id=watermark_model_id,
            )
            final_path, process_info = process_watermark_removal_best_effort(
                temp_path,
                file_type,
                inpaint_config=inpaint_cfg,
            )

        icfg = await resolve_integration_config(db, org_id=current_user.org_id)
        backend = get_write_backend(icfg)
        stored = backend.upload_local_file(
            final_path,
            file_type,
            file.filename or "material.bin",
        )

        row = AssetLibrary(
            user_id=current_user.id,
            title=file.filename or "未命名素材",
            file_type=file_type,
            file_url=stored.public_url,
            source=src,
            storage_platform=stored.storage_platform,
            storage_object_key=stored.object_key,
            file_size=file_size,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)

        access_url = library_row_access_url(row, icfg)
        return MaterialUploadResponse(
            id=row.id,
            title=row.title,
            file_type=MaterialTypeEnum(row.file_type),
            file_url=row.file_url,
            source=row.source,
            storage_platform=row.storage_platform,
            storage_object_key=row.storage_object_key,
            file_size=row.file_size,
            created_at=row.created_at,
            remove_watermark=remove_watermark,
            process_info=process_info,
            access_url=access_url,
        )
    finally:
        remove_temp_dir(tmp_dir)
