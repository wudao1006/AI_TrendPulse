"""Celery任务模块"""
from app.workers.celery_app import celery_app

__all__ = ["celery_app"]
