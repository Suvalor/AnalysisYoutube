"""蓝海雷达参数迭代 Pydantic schemas。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RadarParamIterationCreate(BaseModel):
    """创建迭代记录请求体。"""
    scan_params: dict = Field(..., description="本次扫描使用的参数快照")
    recommended_params: dict | None = Field(None, description="AI 推荐的下一轮参数")
    scan_result_summary: dict | None = Field(None, description="扫描结果摘要")
    iteration_type: str = Field("manual", description="迭代类型：auto/manual")


class RadarParamIterationItem(BaseModel):
    """迭代记录列表项。"""
    id: int
    user_id: int
    org_id: int
    iteration_type: str
    scan_params: dict
    recommended_params: dict | None
    scan_result_summary: dict | None
    iteration_effect: dict | None
    is_applied: bool
    applied_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RadarParamIterationListResponse(BaseModel):
    """迭代记录列表响应。"""
    items: list[RadarParamIterationItem]
    total: int


class RadarParamLatestResponse(BaseModel):
    """最新推荐参数响应。"""
    recommended_params: dict | None
    iteration_count: int
    last_iteration_at: datetime | None


class RadarParamApplyResponse(BaseModel):
    """应用迭代参数响应。"""
    success: bool
    message: str


class AutoRetroRequest(BaseModel):
    """手动触发自动复盘请求。"""
    force: bool = Field(False, description="是否强制执行（忽略周期限制）")


class AutoRetroResponse(BaseModel):
    """自动复盘响应。"""
    iteration_id: int
    recommended_params: dict
    analysis_summary: str
