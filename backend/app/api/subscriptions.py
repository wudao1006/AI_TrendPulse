"""订阅管理API"""
import logging
import math
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Subscription, Task, TaskStatus, AnalysisResult
from app.schemas import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    SubscriptionTrendResponse,
    SubscriptionTrendPoint,
)
from app.collectors import CollectorRegistry
from app.config import get_settings
from app.services.scheduler_service import SchedulerService

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)


def _resolve_intervals(interval_hours: int | None, interval_minutes: int | None) -> tuple[int, int | None]:
    if interval_minutes is not None:
        interval_minutes = max(1, int(interval_minutes))
        interval_hours = max(1, int(math.ceil(interval_minutes / 60)))
        return interval_hours, interval_minutes
    interval_hours = int(interval_hours) if interval_hours is not None else 6
    interval_hours = max(1, interval_hours)
    return interval_hours, None


@router.post("", response_model=SubscriptionResponse)
async def create_subscription(data: SubscriptionCreate, db: Session = Depends(get_db)):
    """
    创建订阅

    创建订阅后会自动添加定时任务，根据配置的间隔时间定期执行采集分析
    """
    # 验证平台
    available_platforms = set(CollectorRegistry.list_platforms())
    for platform in data.platforms:
        if platform not in available_platforms:
            raise HTTPException(status_code=400, detail=f"不支持的平台: {platform}")

    platform_configs = data.platform_configs or {}
    if platform_configs:
        for platform in platform_configs.keys():
            if platform not in data.platforms:
                raise HTTPException(status_code=400, detail=f"平台配置未包含在订阅平台列表: {platform}")
            if platform not in available_platforms:
                raise HTTPException(status_code=400, detail=f"不支持的平台配置: {platform}")

    # 创建订阅记录
    interval_hours, interval_minutes = _resolve_intervals(
        data.interval_hours,
        data.interval_minutes,
    )
    subscription = Subscription(
        keyword=data.keyword,
        platforms=data.platforms,
        language=data.language,
        report_language=data.report_language,
        semantic_sampling=data.semantic_sampling,
        limit=data.limit,
        interval_hours=interval_hours,
        interval_minutes=interval_minutes,
        alert_threshold=data.alert_threshold,
        # 开启调度时设为现在（APScheduler 会立即执行）
        next_run_at=datetime.utcnow() if settings.scheduler_enabled else None,
        platform_configs=platform_configs,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    # 添加定时任务到 APScheduler
    if settings.scheduler_enabled:
        try:
            scheduler = SchedulerService.get_instance()
            scheduler.add_subscription_job(
                subscription_id=str(subscription.id),
                interval_hours=subscription.interval_hours,
                interval_minutes=subscription.interval_minutes,
                run_immediately=True,  # 立即执行首次任务
            )
            job_info = scheduler.get_job_info(str(subscription.id))
            subscription.next_run_at = job_info["next_run_time"] if job_info else None
            db.commit()
            db.refresh(subscription)
            logger.info(f"Created subscription {subscription.id} with scheduled job")
        except Exception as e:
            logger.error(f"Failed to add scheduler job for subscription {subscription.id}: {e}")
            subscription.next_run_at = None
            db.commit()
            # 调度失败不影响订阅创建，但记录错误
    else:
        logger.info("Scheduler disabled; skipping job creation")

    return SubscriptionResponse.model_validate(subscription)


@router.get("", response_model=List[SubscriptionResponse])
async def list_subscriptions(db: Session = Depends(get_db)):
    """列出所有订阅"""
    subscriptions = db.query(Subscription).order_by(Subscription.created_at.desc()).all()
    if settings.scheduler_enabled:
        scheduler = SchedulerService.get_instance()
        for sub in subscriptions:
            if not sub.is_active:
                sub.next_run_at = None
                continue
            job_info = scheduler.get_job_info(str(sub.id))
            sub.next_run_at = job_info["next_run_time"] if job_info else None
    else:
        for sub in subscriptions:
            sub.next_run_at = None
    return [SubscriptionResponse.model_validate(s) for s in subscriptions]


@router.get("/scheduler/status")
async def get_scheduler_status():
    """获取调度器状态"""
    scheduler = SchedulerService.get_instance()
    return {
        "scheduler_enabled": settings.scheduler_enabled,
        **scheduler.get_status(),
    }


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(subscription_id: UUID, db: Session = Depends(get_db)):
    """获取单个订阅"""
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="订阅不存在")
    return SubscriptionResponse.model_validate(subscription)


@router.get("/{subscription_id}/job")
async def get_subscription_job_info(subscription_id: UUID, db: Session = Depends(get_db)):
    """获取订阅的调度任务信息"""
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="订阅不存在")

    scheduler = SchedulerService.get_instance()
    job_info = scheduler.get_job_info(str(subscription_id))

    return {
        "subscription_id": str(subscription_id),
        "is_active": subscription.is_active,
        "interval_hours": subscription.interval_hours,
        "interval_minutes": subscription.interval_minutes,
        "last_run_at": subscription.last_run_at,
        "next_run_at": job_info["next_run_time"] if job_info else None,
        "scheduler": {
            "scheduler_enabled": settings.scheduler_enabled,
            **scheduler.get_status(),
        },
        "job": job_info,
    }


@router.get("/{subscription_id}/trend", response_model=SubscriptionTrendResponse)
async def get_subscription_trend(
    subscription_id: UUID,
    limit: int = Query(default=10, ge=1, le=10),
    db: Session = Depends(get_db),
):
    """获取订阅最近执行趋势"""
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="订阅不存在")

    rows = (
        db.query(
            Task.id,
            AnalysisResult.sentiment_score,
            AnalysisResult.heat_index,
            AnalysisResult.analyzed_at,
        )
        .join(AnalysisResult, AnalysisResult.task_id == Task.id)
        .filter(
            Task.subscription_id == subscription_id,
            Task.status == TaskStatus.COMPLETED,
        )
        .order_by(AnalysisResult.analyzed_at.desc())
        .limit(limit)
        .all()
    )

    points = [
        SubscriptionTrendPoint(
            task_id=row.id,
            sentiment_score=row.sentiment_score,
            heat_index=row.heat_index,
            analyzed_at=row.analyzed_at,
        )
        for row in rows
    ]

    points.reverse()
    return SubscriptionTrendResponse(subscription_id=subscription_id, points=points)


@router.put("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(subscription_id: UUID, data: SubscriptionUpdate, db: Session = Depends(get_db)):
    """
    更新订阅

    支持更新：
    - is_active: 暂停/恢复定时任务
    - interval_hours / interval_minutes: 更新执行间隔
    - 其他字段: 直接更新数据库
    """
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="订阅不存在")

    update_data = data.model_dump(exclude_unset=True)

    # 验证平台
    if "platforms" in update_data:
        available_platforms = set(CollectorRegistry.list_platforms())
        for platform in update_data["platforms"]:
            if platform not in available_platforms:
                raise HTTPException(status_code=400, detail=f"不支持的平台: {platform}")

    if "platform_configs" in update_data:
        available_platforms = set(CollectorRegistry.list_platforms())
        platform_configs = update_data["platform_configs"] or {}
        platforms = update_data.get("platforms", subscription.platforms)
        for platform in platform_configs.keys():
            if platform not in platforms:
                raise HTTPException(status_code=400, detail=f"平台配置未包含在订阅平台列表: {platform}")
            if platform not in available_platforms:
                raise HTTPException(status_code=400, detail=f"不支持的平台配置: {platform}")

    # 记录需要更新调度器的变更
    is_active_changed = "is_active" in update_data and update_data["is_active"] != subscription.is_active
    interval_changed = (
        ("interval_hours" in update_data and update_data["interval_hours"] != subscription.interval_hours)
        or ("interval_minutes" in update_data and update_data["interval_minutes"] != subscription.interval_minutes)
    )
    # 更新数据库
    if "interval_hours" in update_data or "interval_minutes" in update_data:
        interval_hours, interval_minutes = _resolve_intervals(
            update_data.get("interval_hours", subscription.interval_hours),
            update_data.get("interval_minutes", subscription.interval_minutes),
        )
        subscription.interval_hours = interval_hours
        subscription.interval_minutes = interval_minutes
        update_data.pop("interval_hours", None)
        update_data.pop("interval_minutes", None)

    for key, value in update_data.items():
        setattr(subscription, key, value)

    db.commit()
    db.refresh(subscription)

    # 更新 APScheduler 任务
    if settings.scheduler_enabled:
        try:
            scheduler = SchedulerService.get_instance()

            # 处理间隔变更
            if interval_changed:
                scheduler.update_subscription_job(
                    subscription_id=str(subscription_id),
                    interval_hours=subscription.interval_hours,
                    interval_minutes=subscription.interval_minutes,
                )
                logger.info(
                    "Updated subscription job interval: %s -> %sh/%sm",
                    subscription_id,
                    subscription.interval_hours,
                    subscription.interval_minutes,
                )

            # 处理激活状态变更
            if is_active_changed:
                if subscription.is_active:
                    scheduler.resume_subscription_job(str(subscription_id))
                    logger.info(f"Resumed subscription job: {subscription_id}")
                else:
                    scheduler.pause_subscription_job(str(subscription_id))
                    logger.info(f"Paused subscription job: {subscription_id}")

            if not subscription.is_active and (interval_changed or is_active_changed):
                scheduler.pause_subscription_job(str(subscription_id))

            if interval_changed or is_active_changed:
                job_info = scheduler.get_job_info(str(subscription_id))
                if not subscription.is_active:
                    subscription.next_run_at = None
                else:
                    subscription.next_run_at = job_info["next_run_time"] if job_info else None
                db.commit()
                db.refresh(subscription)

        except Exception as e:
            logger.error(f"Failed to update scheduler job for subscription {subscription_id}: {e}")
    else:
        subscription.next_run_at = None
        db.commit()
        db.refresh(subscription)
        logger.info("Scheduler disabled; skipped scheduler update")

    return SubscriptionResponse.model_validate(subscription)


@router.post("/{subscription_id}/trigger")
async def trigger_subscription_now(subscription_id: UUID, db: Session = Depends(get_db)):
    """
    立即触发订阅任务（手动执行）

    不影响正常的定时调度
    """
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="订阅不存在")

    if not subscription.is_active:
        raise HTTPException(status_code=400, detail="订阅已暂停，请先激活")

    # 直接调用触发函数
    from app.services.scheduler_service import trigger_subscription_task
    try:
        trigger_subscription_task(str(subscription_id))
        return {"message": "任务已触发", "subscription_id": str(subscription_id)}
    except Exception as e:
        logger.error(f"Failed to trigger subscription {subscription_id}: {e}")
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")


@router.delete("/{subscription_id}")
async def delete_subscription(subscription_id: UUID, db: Session = Depends(get_db)):
    """
    删除订阅

    同时移除对应的定时任务
    """
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="订阅不存在")

    # 先从调度器移除任务
    if settings.scheduler_enabled:
        try:
            scheduler = SchedulerService.get_instance()
            scheduler.remove_subscription_job(str(subscription_id))
            logger.info(f"Removed scheduler job for subscription: {subscription_id}")
        except Exception as e:
            logger.error(f"Failed to remove scheduler job for subscription {subscription_id}: {e}")

    # 删除数据库记录
    db.delete(subscription)
    db.commit()

    return {"message": "删除成功"}
