"""任务相关的请求/响应模型"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    """创建任务请求"""
    keyword: str = Field(..., min_length=1, max_length=255, description="搜索关键词")
    language: str = Field(default="en", pattern="^(en|zh)$", description="语言")
    report_language: str = Field(
        default="auto",
        pattern="^(auto|[a-zA-Z-]{2,10})$",
        description="报告语言（auto 表示跟随关键词语言）",
    )
    semantic_sampling: bool = Field(default=False, description="语义预选开关")
    limit: int = Field(default=50, ge=10, le=100, description="采集条数")
    platforms: List[str] = Field(..., min_length=1, description="采集平台列表")
    platform_configs: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "keyword": "DeepSeek",
                "language": "en",
                "report_language": "auto",
                "semantic_sampling": False,
                "limit": 50,
                "platforms": ["reddit", "youtube"]
            }
        }


class TaskResponse(BaseModel):
    """创建任务响应"""
    task_id: UUID
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: UUID
    keyword: str
    platforms: List[str]
    status: str
    progress: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RawDataResponse(BaseModel):
    """单条原始数据响应"""
    id: UUID
    platform: str
    content_type: str
    title: Optional[str]
    content: Optional[str]
    author: Optional[str]
    url: Optional[str]
    metrics: Dict[str, Any]
    published_at: Optional[datetime]

    class Config:
        from_attributes = True


class RawDataListResponse(BaseModel):
    """原始数据列表响应"""
    total: int
    page: int
    page_size: int
    data: List[RawDataResponse]


class TaskSummaryResponse(BaseModel):
    """任务列表项响应"""
    task_id: UUID
    keyword: str
    platforms: List[str]
    status: str
    progress: int
    limit_count: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """任务列表响应"""
    total: int
    page: int
    page_size: int
    data: List[TaskSummaryResponse]
