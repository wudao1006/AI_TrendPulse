"""平台管理API"""
from typing import List

from fastapi import APIRouter

from app.collectors import CollectorRegistry

router = APIRouter()


@router.get("", response_model=List[str])
async def list_platforms():
    """获取支持的平台列表"""
    return CollectorRegistry.list_platforms()
