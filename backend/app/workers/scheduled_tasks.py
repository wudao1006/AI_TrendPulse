"""定时任务 (已废弃)

注意：此模块已被 APScheduler 替代。
订阅任务的调度现在由 app/services/scheduler_service.py 管理。

保留此文件仅供参考，不再使用 Celery Beat 轮询机制。
新的实现支持：
- 实时 CRUD 订阅的定时任务
- 精确的时间调度
- 持久化到 PostgreSQL

参见：app/services/scheduler_service.py
"""
from datetime import datetime, timedelta

from celery import shared_task

from app.database import SessionLocal
from app.models import Subscription, Task, TaskStatus


# ==================== 已废弃 ====================
# 以下代码保留供参考，实际调度由 APScheduler 处理
# ==============================================

@shared_task
def check_subscriptions():
    """
    [已废弃] 检查并执行到期的订阅任务

    此任务已被 APScheduler 替代，不再通过 Celery Beat 调用。
    保留此函数仅供参考和回退使用。
    """
    db = SessionLocal()

    try:
        now = datetime.utcnow()

        due_subscriptions = db.query(Subscription).filter(
            Subscription.is_active == True,
            Subscription.next_run_at <= now,
        ).all()

        for subscription in due_subscriptions:
            task = Task(
                keyword=subscription.keyword,
                language=subscription.language,
                limit_count=50,
                platforms=subscription.platforms,
                status=TaskStatus.PENDING,
            )
            db.add(task)
            db.commit()
            db.refresh(task)

            from app.workers.collect_tasks import collect_and_analyze
            celery_task = collect_and_analyze.delay(str(task.id))

            task.celery_task_id = celery_task.id

            subscription.last_run_at = now
            if subscription.interval_minutes:
                subscription.next_run_at = now + timedelta(minutes=subscription.interval_minutes)
            else:
                subscription.next_run_at = now + timedelta(hours=subscription.interval_hours)

            db.commit()

        return {"checked": len(due_subscriptions), "timestamp": now.isoformat()}

    finally:
        db.close()
