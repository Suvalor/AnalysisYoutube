from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserDep, DBSessionDep
from app.crud.inspiration import (
    create_inspiration,
    delete_inspiration,
    get_inspiration,
    list_inspirations,
    update_inspiration,
)
from app.crud.sop import get_sop_script
from app.models.library import AssetLibrary
from app.schemas.inspiration import (
    InspirationCreate,
    InspirationLinkPlotBody,
    InspirationRead,
    InspirationUpdate,
)
from app.services.asset_access_service import library_row_access_url
from app.services.config_manager import resolve_integration_config

router = APIRouter()

_PLACEHOLDER_IMAGE_ONLY = "（图片灵感）"


def _normalize_create_payload(data: dict) -> dict:
    """纯图片时写入占位正文，便于列表与旧逻辑展示。"""
    text = (data.get("content") or "").strip()
    img = (data.get("image_url") or "").strip() or None
    data["image_url"] = img
    if img and not text:
        data["content"] = _PLACEHOLDER_IMAGE_ONLY
    else:
        data["content"] = text or data.get("content") or ""
    return data


async def _finalize_inspiration_read(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    row,
) -> InspirationRead:
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    access: str | None = None
    if getattr(row, "image_asset_id", None):
        ar = await db.get(AssetLibrary, row.image_asset_id)
        if ar is not None and ar.user_id == current_user.id:
            access = library_row_access_url(ar, icfg)
    elif (row.image_url or "").strip():
        access = (row.image_url or "").strip()
    base = InspirationRead.model_validate(row)
    return base.model_copy(update={"image_access_url": access})


@router.get("", response_model=list[InspirationRead])
async def list_inspirations_api(db: DBSessionDep, current_user: CurrentUserDep) -> list[InspirationRead]:
    rows = await list_inspirations(db, current_user.id)
    return [await _finalize_inspiration_read(db, current_user, x) for x in rows]


@router.post("", response_model=InspirationRead, status_code=status.HTTP_201_CREATED)
async def create_inspiration_api(
    payload: InspirationCreate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> InspirationRead:
    data = payload.model_dump()
    iaid = data.pop("image_asset_id", None)
    if iaid is not None:
        ar = await db.get(AssetLibrary, iaid)
        if ar is None or ar.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的图片素材 id")
        data["image_asset_id"] = iaid
        data["image_url"] = ar.file_url
    data = _normalize_create_payload(data)
    if data.get("recorded_at") is None:
        data["recorded_at"] = datetime.now(timezone.utc)
    row = await create_inspiration(db, current_user.id, data)
    await db.commit()
    await db.refresh(row)
    return await _finalize_inspiration_read(db, current_user, row)


@router.get("/{inspiration_id}", response_model=InspirationRead)
async def get_inspiration_api(
    inspiration_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> InspirationRead:
    row = await get_inspiration(db, current_user.id, inspiration_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="灵感不存在")
    return await _finalize_inspiration_read(db, current_user, row)


@router.put("/{inspiration_id}", response_model=InspirationRead)
async def update_inspiration_api(
    inspiration_id: int,
    payload: InspirationUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> InspirationRead:
    row = await get_inspiration(db, current_user.id, inspiration_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="灵感不存在")
    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        return await _finalize_inspiration_read(db, current_user, row)

    content = row.content if "content" not in patch else (patch.get("content") or "")
    image_url = row.image_url
    image_asset_id = row.image_asset_id

    if "image_asset_id" in patch:
        iaid = patch.get("image_asset_id")
        if iaid is None:
            image_asset_id = None
            image_url = patch["image_url"] if "image_url" in patch else None
        else:
            ar = await db.get(AssetLibrary, iaid)
            if ar is None or ar.user_id != current_user.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的图片素材 id")
            image_asset_id = iaid
            image_url = ar.file_url
    elif "image_url" in patch:
        raw_u = patch["image_url"]
        image_url = None if raw_u is None else ((str(raw_u) or "").strip() or None)
        image_asset_id = None

    text = (content or "").strip()
    img = (image_url or "").strip() or None
    if not text and not img:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="更新后须至少保留文字灵感或图片之一",
        )
    if img and not text:
        content = _PLACEHOLDER_IMAGE_ONLY
    else:
        content = text or content or ""

    apply_patch = {**patch, "content": content, "image_url": image_url, "image_asset_id": image_asset_id}
    row = await update_inspiration(db, row, apply_patch)
    await db.commit()
    await db.refresh(row)
    return await _finalize_inspiration_read(db, current_user, row)


@router.delete("/{inspiration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inspiration_api(
    inspiration_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> None:
    row = await get_inspiration(db, current_user.id, inspiration_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="灵感不存在")
    await delete_inspiration(db, row)
    await db.commit()


@router.post("/{inspiration_id}/link-plot", response_model=InspirationRead)
async def link_inspiration_plot_api(
    inspiration_id: int,
    body: InspirationLinkPlotBody,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> InspirationRead:
    row = await get_inspiration(db, current_user.id, inspiration_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="灵感不存在")
    script = await get_sop_script(db, current_user.id, body.plot_id)
    if script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="剧情记录不存在或无权访问")
    row = await update_inspiration(
        db,
        row,
        {"plot_id": body.plot_id, "status": "已生成剧情"},
    )
    await db.commit()
    await db.refresh(row)
    return await _finalize_inspiration_read(db, current_user, row)
