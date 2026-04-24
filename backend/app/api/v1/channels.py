"""频道相关独立路由（与 /api/youtube 解耦）。"""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DBSessionDep
from app.models.youtube import YouTubeChannel, UserCompetitorPool
from app.schemas.discovery import ChannelDiscoverRequest, ChannelDiscoverResponse, DiscoverChannelItem
from app.services.config_manager import resolve_integration_config
from app.services.quota_service import record_api_quota_usage
from app.services.youtube_service import discover_channels_by_keyword
from app.crud.youtube import ensure_competitor_pool, upsert_channel

router = APIRouter()


class AddChannelByIdRequest(BaseModel):
    """通过 channel_id 入库频道。"""
    channel_id: str = Field(..., min_length=1, max_length=64, description="YouTube 频道 ID")
    channel_title: str = Field("", max_length=255, description="频道标题")
    thumbnail_url: str | None = Field(None, description="缩略图 URL")
    subscriber_count: int = Field(0, description="订阅数")
    group_name: str = Field("默认分组", max_length=100, description="分组名称")

    @field_validator("channel_id")
    @classmethod
    def validate_channel_id_format(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("channel_id 仅允许字母、数字、下划线和连字符")
        return v


class AddChannelByIdResponse(BaseModel):
    success: bool
    message: str
    pool_id: int | None = None


@router.post(
    "/add-by-channel-id",
    response_model=AddChannelByIdResponse,
    summary="通过频道ID入库",
)
async def add_channel_by_id(
    body: AddChannelByIdRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> AddChannelByIdResponse:
    """
    通过 YouTube 频道 ID 直接入库到监控池。
    如果频道已存在则复用，不存在则创建。
    如果已在监控池中则返回提示。
    """
    # 查找或创建频道
    stmt = select(YouTubeChannel).where(YouTubeChannel.yt_channel_id == body.channel_id)
    result = await db.execute(stmt)
    channel = result.scalar_one_or_none()

    if channel is None:
        channel = YouTubeChannel(
            yt_channel_id=body.channel_id,
            title=body.channel_title or body.channel_id,
            thumbnail_url=body.thumbnail_url,
            subscriber_count=body.subscriber_count,
        )
        db.add(channel)
        await db.flush()
    else:
        # 更新标题等信息（如果传入了）
        if body.channel_title and body.channel_title != channel.title:
            channel.title = body.channel_title
        if body.thumbnail_url:
            channel.thumbnail_url = body.thumbnail_url
        if body.subscriber_count > 0:
            channel.subscriber_count = body.subscriber_count
        await db.flush()

    # 检查是否已在监控池
    pool_stmt = select(UserCompetitorPool).where(
        UserCompetitorPool.user_id == current_user.id,
        UserCompetitorPool.channel_id == channel.id,
    )
    pool_result = await db.execute(pool_stmt)
    existing_pool = pool_result.scalar_one_or_none()

    if existing_pool:
        return AddChannelByIdResponse(
            success=True,
            message=f"频道「{channel.title}」已在监控池中",
            pool_id=existing_pool.id,
        )

    # 添加到监控池
    pool = await ensure_competitor_pool(
        session=db,
        user_id=current_user.id,
        channel_id=channel.id,
        group_name=body.group_name,
    )
    await db.commit()

    return AddChannelByIdResponse(
        success=True,
        message=f"频道「{channel.title}」已入库",
        pool_id=pool.id,
    )


@router.post(
    "/discover",
    response_model=ChannelDiscoverResponse,
    summary="潜力频道挖掘（仅查询，不落库）",
)
async def discover_channels(
    body: ChannelDiscoverRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> ChannelDiscoverResponse:
    """
    调用 YouTube search.list（高配额）+ channels.list，按订阅上限过滤。
    成功后会记入当日 API 配额用量。
    """
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    result = await discover_channels_by_keyword(
        keyword=body.keyword,
        published_after_days=body.published_after,
        max_subscribers=body.max_subscribers,
        max_results=body.max_results,
        youtube_api_key=icfg.youtube_api_key,
    )
    if result.search_calls > 0:
        await record_api_quota_usage(db, "search", times=result.search_calls)
    if result.channels_list_calls > 0:
        await record_api_quota_usage(db, "channels", times=result.channels_list_calls, part_count=2)
    await db.commit()

    items = [DiscoverChannelItem.model_validate(x) for x in result.items]
    return ChannelDiscoverResponse(items=items, warnings=result.warnings)
