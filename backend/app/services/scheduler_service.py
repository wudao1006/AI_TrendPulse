"""APScheduler 调度服务"""
import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.config import get_settings
from app.database import engine

logger = logging.getLogger(__name__)
SCHEDULER_LOCK_KEY = 762934281


class SchedulerService:
    """
    调度服务 - 单例模式

    负责管理订阅任务的定时调度，支持动态 CRUD：
    - 添加订阅时，创建对应的定时任务
    - 修改订阅时，更新调度间隔
    - 暂停/恢复订阅时，暂停/恢复任务
    - 删除订阅时，移除定时任务
    """

    _instance: Optional["SchedulerService"] = None
    _scheduler: Optional[BackgroundScheduler] = None
    _initialized: bool = False
    _lock_acquired: bool = False
    _lock_connection: Optional[Connection] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "SchedulerService":
        """获取调度服务单例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def init_scheduler(self):
        """初始化调度器（应在应用启动时调用）"""
        if self._initialized:
            logger.warning("Scheduler already initialized")
            return

        settings = get_settings()
        if not settings.scheduler_enabled:
            logger.info("Scheduler disabled by config; init skipped")
            return
        if not self._acquire_scheduler_lock(settings.database_url):
            logger.warning("Scheduler lock not acquired; skipping scheduler start")
            return

        # 配置 JobStore - 使用 PostgreSQL 持久化
        jobstores = {
            'default': SQLAlchemyJobStore(url=settings.database_url)
        }

        # 配置执行器 - 线程池
        executors = {
            'default': ThreadPoolExecutor(10)
        }

        # 任务默认配置
        job_defaults = {
            'coalesce': True,              # 错过的任务合并为一次执行
            'max_instances': 1,            # 同一任务最多同时运行1个实例
            'misfire_grace_time': 3600,    # 错过1小时内的任务仍会执行
        }

        self._scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC',
        )

        # 启动调度器
        self._scheduler.start()
        self._initialized = True
        logger.info("APScheduler initialized successfully")

    def shutdown(self, wait: bool = True):
        """关闭调度器"""
        if self._scheduler and self._initialized:
            self._scheduler.shutdown(wait=wait)
            self._initialized = False
            logger.info("APScheduler shut down")
        self._release_scheduler_lock()

    def _acquire_scheduler_lock(self, database_url: str) -> bool:
        if self._lock_connection:
            return True
        if not database_url.startswith("postgresql"):
            return True
        try:
            conn = engine.connect()
            result = conn.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": SCHEDULER_LOCK_KEY},
            ).scalar()
            self._lock_acquired = bool(result)
            if self._lock_acquired:
                self._lock_connection = conn
                return True
            conn.close()
            return False
        except Exception as e:
            logger.error(f"Failed to acquire scheduler lock: {e}")
            if self._lock_connection:
                self._lock_connection.close()
                self._lock_connection = None
            return False

    def _release_scheduler_lock(self):
        if not self._lock_acquired or not self._lock_connection:
            return
        try:
            self._lock_connection.execute(
                text("SELECT pg_advisory_unlock(:key)"),
                {"key": SCHEDULER_LOCK_KEY},
            )
        except Exception as e:
            logger.warning(f"Failed to release scheduler lock: {e}")
        finally:
            self._lock_connection.close()
            self._lock_connection = None
            self._lock_acquired = False

    def add_subscription_job(
        self,
        subscription_id: str,
        interval_hours: int,
        interval_minutes: Optional[int] = None,
        run_immediately: bool = True,
    ):
        """
        添加订阅定时任务

        Args:
            subscription_id: 订阅ID
            interval_hours: 执行间隔（小时）
            interval_minutes: 执行间隔（分钟），优先于 interval_hours
            run_immediately: 是否立即执行首次任务
        """
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")

        job_id = f"subscription_{subscription_id}"

        # 计算首次运行时间
        next_run_time = datetime.utcnow() if run_immediately else None

        trigger, interval_desc = self._build_interval_trigger(interval_hours, interval_minutes)

        self._scheduler.add_job(
            func=trigger_subscription_task,
            trigger=trigger,
            id=job_id,
            args=[subscription_id],
            next_run_time=next_run_time,
            replace_existing=True,
            name=f"Subscription task for {subscription_id}",
        )

        logger.info("Added subscription job: %s, interval: %s", job_id, interval_desc)

    def update_subscription_job(
        self,
        subscription_id: str,
        interval_hours: int,
        interval_minutes: Optional[int] = None,
    ):
        """
        更新订阅任务的执行间隔

        Args:
            subscription_id: 订阅ID
            interval_hours: 新的执行间隔（小时）
            interval_minutes: 执行间隔（分钟），优先于 interval_hours
        """
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")

        job_id = f"subscription_{subscription_id}"

        try:
            trigger, interval_desc = self._build_interval_trigger(interval_hours, interval_minutes)
            self._scheduler.reschedule_job(
                job_id,
                trigger=trigger,
            )
            logger.info("Updated subscription job: %s, new interval: %s", job_id, interval_desc)
        except Exception as e:
            logger.error(f"Failed to update job {job_id}: {e}")
            # 如果任务不存在，重新添加
            self.add_subscription_job(
                subscription_id,
                interval_hours,
                interval_minutes=interval_minutes,
                run_immediately=False,
            )

    def pause_subscription_job(self, subscription_id: str):
        """暂停订阅任务"""
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")

        job_id = f"subscription_{subscription_id}"

        try:
            self._scheduler.pause_job(job_id)
            logger.info(f"Paused subscription job: {job_id}")
        except Exception as e:
            logger.warning(f"Failed to pause job {job_id}: {e}")

    def resume_subscription_job(self, subscription_id: str):
        """恢复订阅任务"""
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")

        job_id = f"subscription_{subscription_id}"

        try:
            self._scheduler.resume_job(job_id)
            logger.info(f"Resumed subscription job: {job_id}")
        except Exception as e:
            logger.warning(f"Failed to resume job {job_id}: {e}")

    def remove_subscription_job(self, subscription_id: str):
        """移除订阅任务"""
        if not self._scheduler:
            raise RuntimeError("Scheduler not initialized")

        job_id = f"subscription_{subscription_id}"

        try:
            self._scheduler.remove_job(job_id)
            logger.info(f"Removed subscription job: {job_id}")
        except Exception as e:
            logger.warning(f"Failed to remove job {job_id}: {e}")

    def get_job_info(self, subscription_id: str) -> Optional[dict]:
        """获取任务信息"""
        if not self._scheduler:
            return None

        job_id = f"subscription_{subscription_id}"
        job = self._scheduler.get_job(job_id)

        if job:
            return {
                "job_id": job.id,
                "next_run_time": job.next_run_time,
                "trigger": str(job.trigger),
            }
        return None

    def get_all_jobs(self) -> list:
        """获取所有任务"""
        if not self._scheduler:
            return []

        return [
            {
                "job_id": job.id,
                "next_run_time": job.next_run_time,
                "trigger": str(job.trigger),
            }
            for job in self._scheduler.get_jobs()
        ]

    def get_status(self) -> dict:
        """获取调度器状态"""
        job_count = len(self.get_all_jobs()) if self._scheduler else 0
        return {
            "initialized": self._initialized,
            "lock_acquired": self._lock_acquired,
            "job_count": job_count,
        }

    def _build_interval_trigger(
        self,
        interval_hours: int,
        interval_minutes: Optional[int],
    ) -> tuple[IntervalTrigger, str]:
        if interval_minutes and interval_minutes > 0:
            return IntervalTrigger(minutes=interval_minutes), f"{interval_minutes}m"
        return IntervalTrigger(hours=interval_hours), f"{interval_hours}h"


def trigger_subscription_task(subscription_id: str):
    """
    APScheduler 触发的任务函数

    注意：此函数必须保持轻量！
    只负责：查询订阅 → 创建任务记录 → 投递给 Celery
    耗时的采集和分析工作由 Celery Worker 执行
    """
    from uuid import UUID
    from app.database import SessionLocal
    from app.models import Subscription, Task, TaskStatus
    from app.workers.collect_tasks import collect_and_analyze

    logger.info(f"Triggering subscription task: {subscription_id}")

    db = SessionLocal()
    try:
        # 查询订阅
        try:
            subscription_uuid = UUID(subscription_id)
        except ValueError:
            logger.warning(f"Invalid subscription id: {subscription_id}")
            return

        subscription = db.query(Subscription).filter(
            Subscription.id == subscription_uuid
        ).first()

        if not subscription:
            logger.warning(f"Subscription not found: {subscription_id}")
            return

        if not subscription.is_active:
            logger.info(f"Subscription is inactive: {subscription_id}")
            return

        # 创建任务记录
        task = Task(
            subscription_id=subscription.id,
            keyword=subscription.keyword,
            language=subscription.language,
            report_language=subscription.report_language or "auto",
            semantic_sampling=subscription.semantic_sampling,
            limit_count=subscription.limit,
            platforms=subscription.platforms,
            platform_configs=subscription.platform_configs or {},
            status=TaskStatus.PENDING,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        logger.info(f"Created task {task.id} for subscription {subscription_id}")

        # 投递给 Celery Worker（立即返回，不阻塞）
        celery_task = collect_and_analyze.delay(str(task.id))

        # 更新任务的 Celery Task ID
        task.celery_task_id = celery_task.id

        # 更新订阅的最后执行时间
        subscription.last_run_at = datetime.utcnow()
        job_info = SchedulerService.get_instance().get_job_info(str(subscription.id))
        subscription.next_run_at = job_info["next_run_time"] if job_info else None

        db.commit()

        logger.info(f"Dispatched Celery task {celery_task.id} for task {task.id}")

    except Exception as e:
        logger.error(f"Error triggering subscription task {subscription_id}: {e}")
        raise
    finally:
        db.close()
