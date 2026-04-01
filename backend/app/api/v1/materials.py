from datetime import datetime, time

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DBSessionDep
from app.models.library import AssetLibrary
from app.schemas.materials import MaterialRead, MaterialTypeEnum, MaterialUploadResponse
from app.services.material_service import (
    infer_file_type,
    process_watermark_removal,
    remove_temp_dir,
    save_upload_to_temp,
    upload_to_oss,
)


router = APIRouter()


@router.get("", response_model=list[MaterialRead])
async def list_materials(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    type: MaterialTypeEnum | None = Query(default=None, description="文件类型：image/video"),
    start_date: str | None = Query(default=None, description="开始日期，格式 YYYY-MM-DD"),
    end_date: str | None = Query(default=None, description="结束日期，格式 YYYY-MM-DD"),
) -> list[MaterialRead]:
    query = select(AssetLibrary).where(AssetLibrary.user_id == current_user.id)
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
    return [MaterialRead.model_validate(x) for x in rows]


@router.post("/upload", response_model=MaterialUploadResponse)
async def upload_material(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    file: UploadFile = File(...),
    remove_watermark: bool = Form(default=False),
) -> MaterialUploadResponse:
    raw_bytes = await file.read()
    file_size = len(raw_bytes)
    file_type = infer_file_type(file.content_type)

    tmp_dir = ""
    try:
        tmp_dir, temp_path = save_upload_to_temp(file.filename or "upload.bin", raw_bytes)
        final_path = temp_path
        if remove_watermark:
            final_path = process_watermark_removal(temp_path, file_type)

        oss_url = upload_to_oss(
            final_file_path=final_path,
            file_type=file_type,
            original_name=file.filename or "material.bin",
        )

        row = AssetLibrary(
            user_id=current_user.id,
            title=file.filename or "未命名素材",
            file_type=file_type,
            file_url=oss_url,
            file_size=file_size,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)

        return MaterialUploadResponse(
            id=row.id,
            title=row.title,
            file_type=MaterialTypeEnum(row.file_type),
            file_url=row.file_url,
            file_size=row.file_size,
            created_at=row.created_at,
            remove_watermark=remove_watermark,
        )
    finally:
        remove_temp_dir(tmp_dir)
