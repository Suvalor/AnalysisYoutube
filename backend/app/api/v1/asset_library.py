from datetime import date, datetime, time, timezone
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import asc, desc, func, nulls_first, nulls_last, select

from app.api.deps import CurrentUserDep, DBSessionDep
from app.constants.asset_source import ALLOWED_ASSET_SOURCES, ASSET_SOURCE_MANUAL
from app.crud.library import create_with_user, delete_with_user, ensure_owned_or_404, get_by_user, update_with_user
from app.models.library import AssetLibrary
from app.schemas.library import (
    AssetAccessUrlResponse,
    AssetCreate,
    AssetFileTypeEnum,
    AssetListResponse,
    AssetPresignUploadRequest,
    AssetPresignUploadResponse,
    AssetRead,
    AssetUpdate,
    AssetUploadResponse,
)
from app.services.asset_access_service import library_row_access_url
from app.services.config_manager import resolve_integration_config
from app.services.material_service import (
    infer_asset_library_file_type,
    infer_asset_library_file_type_loose,
    process_watermark_removal_best_effort,
    remove_temp_dir,
    save_upload_to_temp,
)
from app.services.watermark_inpaint_config import resolve_inpaint_runtime_config
from app.services.object_storage import build_material_object_key, get_write_backend, material_access_url

router = APIRouter()


def _normalize_upload_source(raw: str) -> str:
    s = (raw or ASSET_SOURCE_MANUAL).strip().upper()
    return s if s in ALLOWED_ASSET_SOURCES else ASSET_SOURCE_MANUAL


async def _asset_read_with_access(db: DBSessionDep, current_user: CurrentUserDep, row: AssetLibrary) -> AssetRead:
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    au = library_row_access_url(row, icfg)
    return AssetRead.model_validate(row).model_copy(update={"access_url": au})


def _asset_list_conditions(
    *,
    user_id: int,
    file_type: AssetFileTypeEnum | None,
    date_start: date | None,
    date_end: date | None,
    q: str | None,
) -> list:
    cond = [
        AssetLibrary.user_id == user_id,
        AssetLibrary.source == ASSET_SOURCE_MANUAL,
    ]
    if file_type is not None:
        cond.append(AssetLibrary.file_type == file_type.value)
    if date_start is not None:
        start = datetime.combine(date_start, time.min, tzinfo=timezone.utc)
        cond.append(AssetLibrary.created_at >= start)
    if date_end is not None:
        end = datetime.combine(date_end, time.max, tzinfo=timezone.utc)
        cond.append(AssetLibrary.created_at <= end)
    qt = (q or "").strip()
    if qt:
        cond.append(AssetLibrary.title.contains(qt))
    return cond


@router.get("", response_model=AssetListResponse)
async def list_assets(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    file_type: AssetFileTypeEnum | None = Query(None, description="按类型筛选：image / video / audio"),
    date_start: date | None = Query(None, description="上传时间起（含当日 0 点，UTC）"),
    date_end: date | None = Query(None, description="上传时间止（含当日，UTC）"),
    q: str | None = Query(None, max_length=255, description="标题模糊搜索"),
    sort_by: Literal["created_at", "file_size"] = Query("created_at", description="排序字段"),
    sort_order: Literal["asc", "desc"] = Query("desc", description="升序/降序"),
) -> AssetListResponse:
    """素材库主列表：仅 MANUAL；支持分页、类型/时间/关键词筛选与排序。"""
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    conditions = _asset_list_conditions(
        user_id=current_user.id,
        file_type=file_type,
        date_start=date_start,
        date_end=date_end,
        q=q,
    )

    count_stmt = select(func.count()).select_from(AssetLibrary).where(*conditions)
    total = int((await db.execute(count_stmt)).scalar_one() or 0)

    stmt = select(AssetLibrary).where(*conditions)
    if sort_by == "file_size":
        if sort_order == "desc":
            stmt = stmt.order_by(nulls_last(desc(AssetLibrary.file_size)), desc(AssetLibrary.id))
        else:
            stmt = stmt.order_by(nulls_first(asc(AssetLibrary.file_size)), asc(AssetLibrary.id))
    else:
        if sort_order == "desc":
            stmt = stmt.order_by(desc(AssetLibrary.created_at), desc(AssetLibrary.id))
        else:
            stmt = stmt.order_by(asc(AssetLibrary.created_at), asc(AssetLibrary.id))

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    items = [
        AssetRead.model_validate(r).model_copy(update={"access_url": library_row_access_url(r, icfg)})
        for r in rows
    ]
    return AssetListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post("/get_upload_params", response_model=AssetPresignUploadResponse)
async def get_upload_params(
    body: AssetPresignUploadRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    expires: int = Query(600, ge=60, le=3600, description="预签名有效秒数"),
) -> AssetPresignUploadResponse:
    """
    浏览器直传：返回 PUT 预签名 URL（Host 为云厂商端点，勿改写）。
    前端 PUT 成功后请调用 `POST /api/assets` 落库（带上 storage_platform、storage_object_key、final_access_url 等）。
    请在 OSS/COS 控制台配置 CORS：允许来源为你的前端域名、方法含 PUT、暴露 ETag 等。
    """
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    backend = get_write_backend(icfg)
    ft = infer_asset_library_file_type_loose(body.content_type, body.filename)
    object_key = build_material_object_key(ft, body.filename)
    upload_url, required_headers = backend.presigned_put_url(object_key, expires, body.content_type)
    final_access_url = backend.material_record_url(object_key)
    return AssetPresignUploadResponse(
        upload_url=upload_url,
        final_access_url=final_access_url,
        storage_platform=backend.platform,
        storage_object_key=object_key,
        file_type=AssetFileTypeEnum(ft),
        expires_in=expires,
        required_headers=required_headers,
    )


@router.post("/upload", response_model=AssetUploadResponse)
async def upload_asset(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    file: UploadFile = File(...),
    remove_watermark: bool = Form(default=False),
    source: str = Form(default=ASSET_SOURCE_MANUAL),
) -> AssetUploadResponse:
    """
    按组织配置选择云厂商上传。source：MANUAL=素材库默认；SOP=SOP 内上传（仍落库但不出现在素材库列表）。
    """
    raw_bytes = await file.read()
    file_size = len(raw_bytes)
    file_type = infer_asset_library_file_type(file.content_type)
    src = _normalize_upload_source(source)

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
            file.filename or "asset.bin",
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
        return AssetUploadResponse(
            id=row.id,
            title=row.title,
            file_type=AssetFileTypeEnum(row.file_type),
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


@router.get("/{asset_id}/access-url", response_model=AssetAccessUrlResponse)
async def get_asset_access_url(
    asset_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    expires: int = Query(default=3600, ge=60, le=86400, description="签名 URL 有效秒数"),
) -> AssetAccessUrlResponse:
    result = await db.execute(
        select(AssetLibrary).where(
            AssetLibrary.id == asset_id,
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
    return AssetAccessUrlResponse(
        url=url,
        mode=mode,
        expires_in=expires if mode == "presigned" else None,
    )


@router.get("/{asset_id}", response_model=AssetRead)
async def get_asset(asset_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> AssetRead:
    row = ensure_owned_or_404(await get_by_user(db, AssetLibrary, current_user.id, asset_id))
    return await _asset_read_with_access(db, current_user, row)


@router.post("", response_model=AssetRead)
async def create_asset(payload: AssetCreate, db: DBSessionDep, current_user: CurrentUserDep) -> AssetRead:
    data = payload.model_dump()
    s = (data.get("source") or ASSET_SOURCE_MANUAL).strip().upper()
    data["source"] = s if s in ALLOWED_ASSET_SOURCES else ASSET_SOURCE_MANUAL
    row = await create_with_user(db, AssetLibrary, current_user.id, data)
    return await _asset_read_with_access(db, current_user, row)


@router.put("/{asset_id}", response_model=AssetRead)
async def update_asset(
    asset_id: int,
    payload: AssetUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> AssetRead:
    row = ensure_owned_or_404(await get_by_user(db, AssetLibrary, current_user.id, asset_id))
    row = await update_with_user(db, row, payload.model_dump(exclude_unset=True))
    return await _asset_read_with_access(db, current_user, row)


@router.delete("/{asset_id}")
async def delete_asset(asset_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> dict[str, str]:
    row = ensure_owned_or_404(await get_by_user(db, AssetLibrary, current_user.id, asset_id))
    await delete_with_user(db, row)
    return {"message": "删除成功"}
