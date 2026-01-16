"""Celery应用配置"""
import socket

from celery import Celery

from app.config import get_settings

settings = get_settings()


def _build_socket_keepalive_options() -> dict:
    options = {}
    if hasattr(socket, "TCP_KEEPIDLE"):
        options[socket.TCP_KEEPIDLE] = 600
    if hasattr(socket, "TCP_KEEPINTVL"):
        options[socket.TCP_KEEPINTVL] = 30
    if hasattr(socket, "TCP_KEEPCNT"):
        options[socket.TCP_KEEPCNT] = 3
    return options


SOCKET_KEEPALIVE_OPTIONS = _build_socket_keepalive_options()

celery_app = Celery(
    "ai_sentiment",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.collect_tasks",
        "app.workers.analyze_tasks",
        "app.workers.scheduled_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,
    result_backend_thread_safe=True,
    result_backend_always_retry=True,
    result_backend_max_retries=10,
    broker_heartbeat=10,
    broker_heartbeat_checkrate=2,
    redis_backend_health_check_interval=10,
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    broker_transport_options={
        "socket_keepalive": True,
        "socket_keepalive_options": SOCKET_KEEPALIVE_OPTIONS,
        "socket_connect_timeout": 60,
        "socket_timeout": 60,
        "retry_on_timeout": True,
        "health_check_interval": 10,
        "visibility_timeout": 3600,
    },
    result_backend_transport_options={
        "socket_keepalive": True,
        "socket_keepalive_options": SOCKET_KEEPALIVE_OPTIONS,
        "socket_connect_timeout": 60,
        "socket_timeout": 60,
        "retry": True,
        "health_check_interval": 10,
        "retry_policy": {
            "max_retries": 5,
            "interval_start": 0.5,
            "interval_step": 1,
            "interval_max": 10,
        },
    },
    task_queue_max_priority=10,
)

# 注意：定时任务调度已迁移至 APScheduler
# 不再使用 Celery Beat，订阅任务由 SchedulerService 管理
# 参见 app/services/scheduler_service.py
