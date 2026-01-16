"""分析结果相关的请求/响应模型"""
from datetime import datetime
from typing import List, Dict, Optional
from uuid import UUID

from pydantic import BaseModel


class KeyOpinion(BaseModel):
    """核心观点"""
    title: str
    description: str
    points: List[str] = []


class AnalysisResultResponse(BaseModel):
    """分析结果响应"""
    task_id: UUID
    sentiment_score: int
    key_opinions: List[KeyOpinion]
    summary: str
    mermaid_code: Optional[str]
    heat_index: float
    total_items: int
    platform_distribution: Dict[str, int]
    analyzed_at: datetime

    class Config:
        from_attributes = True
