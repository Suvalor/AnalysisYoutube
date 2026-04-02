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
from app.schemas.inspiration import (
    InspirationCreate,
    InspirationLinkPlotBody,
    InspirationRead,
    InspirationUpdate,
)


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


@router.get("", response_model=list[InspirationRead])
async def list_inspirations_api(db: DBSessionDep, current_user: CurrentUserDep) -> list[InspirationRead]:
    rows = await list_inspirations(db, current_user.id)
    return [InspirationRead.model_validate(x) for x in rows]


@router.post("", response_model=InspirationRead, status_code=status.HTTP_201_CREATED)
async def create_inspiration_api(
    payload: InspirationCreate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> InspirationRead:
    data = _normalize_create_payload(payload.model_dump())
    if data.get("recorded_at") is None:
        data["recorded_at"] = datetime.now(timezone.utc)
    row = await create_inspiration(db, current_user.id, data)
    await db.commit()
    return InspirationRead.model_validate(row)


@router.get("/{inspiration_id}", response_model=InspirationRead)
async def get_inspiration_api(
    inspiration_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> InspirationRead:
    row = await get_inspiration(db, current_user.id, inspiration_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="灵感不存在")
    return InspirationRead.model_validate(row)


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
        return InspirationRead.model_validate(row)

    new_content = (patch["content"] if "content" in patch else row.content) or ""
    new_content = new_content.strip()
    if "image_url" in patch:
        raw_u = patch["image_url"]
        new_image = None if raw_u is None else ((str(raw_u) or "").strip() or None)
    else:
        new_image = row.image_url

    if not new_content and not new_image:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="更新后须至少保留文字灵感或图片之一",
        )
    if new_image and not new_content:
        new_content = _PLACEHOLDER_IMAGE_ONLY

    apply_patch = {**patch, "content": new_content}
    if "image_url" in patch:
        apply_patch["image_url"] = new_image
    row = await update_inspiration(db, row, apply_patch)
    await db.commit()
    await db.refresh(row)
    return InspirationRead.model_validate(row)


@router.delete("/{inspiration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inspiration_api(
    inspiration_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> None:
    """
    删除灵感记录。图片若已上传至 OSS，与素材库策略一致：不在此接口删除远端对象，
    避免误删仍被其他功能引用的同一 URL。
    """
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
    """将灵感标记为已生成剧情，并关联 sop_scripts 主键（plot_id）。"""
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
    return InspirationRead.model_validate(row)
