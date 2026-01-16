"""任务相关API"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Task, TaskStatus, RawData, AnalysisResult
from app.schemas import (
    TaskCreate,
    TaskResponse,
    TaskStatusResponse,
    RawDataListResponse,
    RawDataResponse,
    AnalysisResultResponse,
    KeyOpinion,
    TaskListResponse,
    TaskSummaryResponse,
)
from app.collectors import CollectorRegistry
from app.analyzers.mermaid import MermaidGenerator
from app.analyzers.llm_validators import validate_mermaid_output

router = APIRouter()


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """任务列表（按时间倒序）"""
    query = db.query(Task)

    if status:
        try:
            status_enum = TaskStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效状态: {status}")
        query = query.filter(Task.status == status_enum)

    if keyword:
        query = query.filter(Task.keyword.ilike(f"%{keyword}%"))

    total = query.count()
    tasks = (
        query.order_by(Task.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return TaskListResponse(
        total=total,
        page=page,
        page_size=page_size,
        data=[
            TaskSummaryResponse(
                task_id=task.id,
                keyword=task.keyword,
                platforms=task.platforms,
                status=task.status.value,
                progress=task.progress,
                limit_count=task.limit_count,
                error_message=task.error_message,
                created_at=task.created_at,
                updated_at=task.updated_at,
            )
            for task in tasks
        ],
    )


@router.post("", response_model=TaskResponse)
async def create_task(task_data: TaskCreate, db: Session = Depends(get_db)):
    """创建新的采集分析任务"""
    available_platforms = set(CollectorRegistry.list_platforms())
    for platform in task_data.platforms:
        if platform not in available_platforms:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的平台: {platform}，支持的平台: {sorted(available_platforms)}"
            )

    platform_configs = task_data.platform_configs or {}
    if platform_configs:
        for platform in platform_configs.keys():
            if platform not in task_data.platforms:
                raise HTTPException(status_code=400, detail=f"平台配置未包含在任务平台列表: {platform}")
            if platform not in available_platforms:
                raise HTTPException(status_code=400, detail=f"不支持的平台配置: {platform}")

    task = Task(
        keyword=task_data.keyword,
        language=task_data.language,
        report_language=task_data.report_language,
        semantic_sampling=task_data.semantic_sampling,
        limit_count=task_data.limit,
        platforms=task_data.platforms,
        platform_configs=platform_configs,
        status=TaskStatus.PENDING,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    from app.workers.collect_tasks import collect_and_analyze
    celery_task = collect_and_analyze.delay(str(task.id))

    task.celery_task_id = celery_task.id
    db.commit()

    return TaskResponse(
        task_id=task.id,
        status=task.status.value,
        created_at=task.created_at,
    )


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: UUID, db: Session = Depends(get_db)):
    """查询任务状态"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return TaskStatusResponse(
        task_id=task.id,
        keyword=task.keyword,
        platforms=task.platforms,
        status=task.status.value,
        progress=task.progress,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.delete("/{task_id}")
async def delete_task(task_id: UUID, db: Session = Depends(get_db)):
    """删除任务及其关联数据"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status in {TaskStatus.PENDING, TaskStatus.RUNNING}:
        raise HTTPException(status_code=409, detail="任务进行中，无法删除")

    db.delete(task)
    db.commit()
    return {"status": "deleted"}


@router.get("/{task_id}/result", response_model=AnalysisResultResponse)
async def get_task_result(task_id: UUID, db: Session = Depends(get_db)):
    """获取分析结果"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"任务尚未完成，当前状态: {task.status.value}")

    result = db.query(AnalysisResult).filter(AnalysisResult.task_id == task_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="分析结果不存在")

    mermaid_code = result.mermaid_code
    if mermaid_code:
        valid, _ = validate_mermaid_output(mermaid_code)
        if not valid:
            mermaid_code = MermaidGenerator().build_safe_mindmap(
                keyword=task.keyword,
                key_opinions=result.key_opinions,
                sentiment_score=result.sentiment_score,
            )

    return AnalysisResultResponse(
        task_id=result.task_id,
        sentiment_score=result.sentiment_score,
        key_opinions=[KeyOpinion(**op) for op in result.key_opinions],
        summary=result.summary,
        mermaid_code=mermaid_code,
        heat_index=result.heat_index,
        total_items=result.total_items,
        platform_distribution=result.platform_distribution,
        analyzed_at=result.analyzed_at,
    )


@router.get("/{task_id}/raw-data", response_model=RawDataListResponse)
async def get_raw_data(
    task_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    platform: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """获取原始采集数据"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    query = db.query(RawData).filter(RawData.task_id == task_id)

    if platform:
        query = query.filter(RawData.platform == platform)

    total = query.count()
    data = query.offset((page - 1) * page_size).limit(page_size).all()

    return RawDataListResponse(
        total=total,
        page=page,
        page_size=page_size,
        data=[RawDataResponse(
            id=item.id,
            platform=item.platform.value,
            content_type=item.content_type.value,
            title=item.title,
            content=item.content,
            author=item.author,
            url=item.url,
            metrics=item.metrics,
            published_at=item.published_at,
        ) for item in data],
    )
