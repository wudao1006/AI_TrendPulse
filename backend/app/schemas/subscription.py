"""订阅相关的请求/响应模型"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


class SubscriptionCreate(BaseModel):
    """创建订阅请求"""
    keyword: str = Field(..., min_length=1, max_length=255)
    platforms: List[str] = Field(..., min_length=1)
    language: str = Field(default="en", pattern="^(en|zh)$")
    report_language: str = Field(
        default="auto",
        pattern="^(auto|[a-zA-Z-]{2,10})$",
    )
    semantic_sampling: bool = Field(default=False)
    limit: int = Field(default=50, ge=10, le=200)
    interval_hours: Optional[int] = Field(default=6, ge=0, le=24)
    interval_minutes: Optional[int] = Field(default=None, ge=1, le=1440)
    alert_threshold: int = Field(default=30, ge=0, le=100)
    platform_configs: Optional[Dict[str, Any]] = None


class SubscriptionUpdate(BaseModel):
    """更新订阅请求"""
    keyword: Optional[str] = Field(None, min_length=1, max_length=255)
    platforms: Optional[List[str]] = None
    language: Optional[str] = Field(None, pattern="^(en|zh)$")
    report_language: Optional[str] = Field(
        None,
        pattern="^(auto|[a-zA-Z-]{2,10})$",
    )
    semantic_sampling: Optional[bool] = None
    limit: Optional[int] = Field(None, ge=10, le=200)
    interval_hours: Optional[int] = Field(None, ge=0, le=24)
    interval_minutes: Optional[int] = Field(None, ge=1, le=1440)
    alert_threshold: Optional[int] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None
    platform_configs: Optional[Dict[str, Any]] = None


class SubscriptionResponse(BaseModel):
    """订阅响应"""
    id: UUID
    keyword: str
    platforms: List[str]
    language: str
    report_language: str
    semantic_sampling: bool
    limit: int
    interval_hours: int
    interval_minutes: Optional[int]
    alert_threshold: int
    is_active: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    created_at: datetime
    platform_configs: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    """报警响应"""
    id: UUID
    subscription_id: UUID
    task_id: Optional[UUID]
    sentiment_score: int
    alert_type: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SubscriptionTrendPoint(BaseModel):
    """订阅趋势点"""
    task_id: UUID
    sentiment_score: int
    heat_index: float
    analyzed_at: datetime


class SubscriptionTrendResponse(BaseModel):
    """订阅趋势响应"""
    subscription_id: UUID
    points: List[SubscriptionTrendPoint]
