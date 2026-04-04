from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import JSONResponse

from app.api.deps import CurrentUserDep, DBSessionDep
from app.crud.feishu_doc import create_feishu_doc, delete_feishu_doc, get_feishu_doc, list_feishu_docs
from app.schemas.feishu_doc import FeishuDocArchiveTriggerResponse, FeishuDocCreate, FeishuDocListResponse, FeishuDocRead
from app.services.feishu_doc_archive import run_feishu_doc_archive_task


router = APIRouter()


@router.get("", response_model=FeishuDocListResponse, summary="获取飞书文档列表（分页 + 搜索）")
async def list_docs(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    search: str | None = Query(None, max_length=255, description="按标题模糊搜索"),
) -> FeishuDocListResponse:
    rows, total = await list_feishu_docs(
        db,
        org_id=current_user.org_id,
        page=page,
        page_size=page_size,
        search=search,
    )
    return FeishuDocListResponse(
        items=[FeishuDocRead.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=FeishuDocRead, summary="新增飞书文档")
async def create_doc(
    body: FeishuDocCreate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> FeishuDocRead:
    row = await create_feishu_doc(
        db,
        org_id=current_user.org_id,
        title=body.title.strip(),
        url=body.url.strip(),
    )
    await db.commit()
    await db.refresh(row)
    return FeishuDocRead.model_validate(row)


@router.get("/{doc_id}", response_model=FeishuDocRead, summary="获取单个飞书文档")
async def get_doc(
    doc_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> FeishuDocRead:
    row = await get_feishu_doc(db, org_id=current_user.org_id, doc_id=doc_id)
    if row is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    return FeishuDocRead.model_validate(row)


@router.delete("/{doc_id}", summary="删除飞书文档")
async def delete_doc(
    doc_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> dict:
    ok = await delete_feishu_doc(db, org_id=current_user.org_id, doc_id=doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail="文档不存在")
    await db.commit()
    return {"success": True}


@router.post(
    "/{doc_id}/archive",
    response_model=FeishuDocArchiveTriggerResponse,
    summary="异步离线归档飞书文档（202 Accepted）",
)
async def archive_doc(
    doc_id: int,
    background_tasks: BackgroundTasks,
    db: DBSessionDep,
    current_user: CurrentUserDep,
):
    row = await get_feishu_doc(db, org_id=current_user.org_id, doc_id=doc_id)
    if row is None:
        raise HTTPException(status_code=404, detail="文档不存在")

    if row.archive_status == "ARCHIVING":
        raise HTTPException(status_code=409, detail="文档正在归档中，请稍候")

    if row.archive_status == "SUCCESS":
        return JSONResponse(
            status_code=200,
            content=FeishuDocArchiveTriggerResponse(
                status="already_archived",
                doc_id=doc_id,
                message="该文档已成功归档",
            ).model_dump(),
        )

    row.archive_status = "ARCHIVING"
    await db.commit()

    org_id = current_user.org_id
    background_tasks.add_task(run_feishu_doc_archive_task, doc_id=doc_id, org_id=org_id)

    return JSONResponse(
        status_code=202,
        content=FeishuDocArchiveTriggerResponse(
            status="accepted",
            doc_id=doc_id,
            message="归档任务已排队（后台校验 PDF 有效后才会标记成功，请留意列表状态）",
        ).model_dump(),
    )

