"""FastAPI应用入口"""
import logging
import os
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api import tasks, platforms, subscriptions, alerts
from app.api.deps import require_api_key
from app.database import SessionLocal
from app.models import Subscription
from app.services.scheduler_service import SchedulerService

settings = get_settings()
logger = logging.getLogger(__name__)

# 配置日志
def setup_logging():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)

    # 1. 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 2. 文件轮转处理器 (10MB * 5 backups)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        handlers=[console_handler, file_handler]
    )

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    启动时：
    1. 初始化 APScheduler
    2. 从数据库恢复所有活跃订阅的定时任务

    关闭时：
    1. 优雅关闭 APScheduler
    """
    # ========== 启动逻辑 ==========
    logger.info("Starting application...")

    scheduler = SchedulerService.get_instance()
    if settings.scheduler_enabled:
        # 初始化调度器
        scheduler.init_scheduler()

        # 从数据库恢复活跃订阅的调度任务
        db = SessionLocal()
        try:
            active_subscriptions = db.query(Subscription).filter(
                Subscription.is_active == True
            ).all()

            restored_count = 0
            for sub in active_subscriptions:
                try:
                    scheduler.add_subscription_job(
                        subscription_id=str(sub.id),
                        interval_hours=sub.interval_hours,
                        interval_minutes=sub.interval_minutes,
                        run_immediately=False,  # 启动时不立即执行，等待正常调度
                    )
                    restored_count += 1
                except Exception as e:
                    logger.error(f"Failed to restore subscription job {sub.id}: {e}")

            logger.info(f"Restored {restored_count}/{len(active_subscriptions)} subscription jobs")

        except Exception as e:
            logger.error(f"Error restoring subscription jobs: {e}")
        finally:
            db.close()
    else:
        logger.info("Scheduler disabled by config; skipping init")

    logger.info("Application startup complete")

    yield  # 应用运行中

    # ========== 关闭逻辑 ==========
    logger.info("Shutting down application...")

    # 优雅关闭调度器（等待当前任务完成）
    if settings.scheduler_enabled:
        scheduler.shutdown(wait=True)

    logger.info("Application shutdown complete")


app = FastAPI(
    title="AI舆情分析系统",
    description="多源数据采集与AI智能分析API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
    dependencies=[Depends(require_api_key)],
)

# CORS配置
# 注意：生产环境应配置具体的 allow_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: 生产环境改为具体域名
    allow_credentials=False,  # 使用 * 时必须为 False
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """健康检查接口"""
    scheduler = SchedulerService.get_instance()
    jobs = scheduler.get_all_jobs()
    scheduler_status = scheduler.get_status()

    return {
        "status": "healthy",
        "version": "1.0.0",
        "scheduler": {
            "active_jobs": len(jobs),
            "scheduler_enabled": settings.scheduler_enabled,
            **scheduler_status,
        }
    }


@app.get("/scheduler/jobs")
async def list_scheduler_jobs():
    """列出所有调度任务（调试用）"""
    scheduler = SchedulerService.get_instance()
    return {
        "jobs": scheduler.get_all_jobs()
    }


# 注册路由
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["任务管理"])
app.include_router(platforms.router, prefix="/api/v1/platforms", tags=["平台管理"])
app.include_router(subscriptions.router, prefix="/api/v1/subscriptions", tags=["订阅管理"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["报警管理"])
