"""采集任务"""
import asyncio
import logging
import time
from typing import List
from uuid import UUID

from celery import shared_task, chord
from celery.exceptions import CeleryError
from kombu.exceptions import OperationalError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Task, TaskStatus, RawData, Platform, ContentType
from app.collectors import CollectorRegistry
from app.collectors.base import CollectedItem

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def collect_and_analyze(self, task_id: str):
    """采集并分析任务"""
    db = SessionLocal()

    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"error": "Task not found"}

        task.status = TaskStatus.RUNNING
        task.progress = 5
        db.commit()

        platforms = task.platforms or []
        if not platforms:
            task.status = TaskStatus.FAILED
            task.error_message = "No platforms configured"
            db.commit()
            return {"error": "No platforms configured"}

        platform_configs = task.platform_configs or {}
        per_platform_limit = max(1, task.limit_count // max(len(platforms), 1))
        task.progress = 10
        db.commit()

        collection_tasks = []
        for platform in platforms:
            config = platform_configs.get(platform, {}) if isinstance(platform_configs, dict) else {}
            override_limit = config.get("limit")
            if isinstance(override_limit, int) and override_limit > 0:
                platform_limit = override_limit
            else:
                platform_limit = per_platform_limit

            collection_tasks.append(
                collect_platform_data.s(
                    task_id=str(task.id),
                    platform=platform,
                    keyword=task.keyword,
                    limit=platform_limit,
                    language=task.language,
                    platform_config=config,
                )
            )

        if not collection_tasks:
            task.status = TaskStatus.FAILED
            task.error_message = "No valid collectors"
            db.commit()
            return {"error": "No valid collectors"}

        chord(collection_tasks)(finalize_collection.s(str(task.id)))
        return {
            "status": "collecting_dispatched",
            "platforms": platforms,
        }

    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        db.commit()
        raise
    finally:
        db.close()


async def _collect_single_platform(
    keyword: str,
    limit: int,
    language: str,
    platform: str,
    platform_config: dict,
) -> List[CollectedItem]:
    """采集单个平台"""
    from app.config import get_settings
    settings = get_settings()

    collector = CollectorRegistry.get_instance(
        platform,
        config={
            "reddit_client_id": settings.reddit_client_id,
            "reddit_client_secret": settings.reddit_client_secret,
            "youtube_api_key": settings.youtube_api_key,
            "x_accounts_path": settings.x_accounts_path,
            "x_accounts_json": settings.x_accounts_json,
            "x_headless": settings.x_headless,
            "x_proxy": settings.x_proxy,
            "x_user_agent": settings.x_user_agent,
            "x_timeout_ms": settings.x_timeout_ms,
            "x_account_error_limit": settings.x_account_error_limit,
            "platform_config": platform_config,
        }
    )

    if not collector:
        logger.warning("Collector not found for platform: %s", platform)
        return []

    try:
        return await collector.collect(keyword, limit, language)
    except Exception as exc:
        logger.warning("Error collecting from %s: %s", platform, exc)
        return []


def _collect_single_platform_sync(
    keyword: str,
    limit: int,
    language: str,
    platform: str,
    platform_config: dict,
) -> List[CollectedItem]:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            _collect_single_platform(
                keyword=keyword,
                limit=limit,
                language=language,
                platform=platform,
                platform_config=platform_config,
            )
        )
    finally:
        loop.close()


@shared_task(bind=True, max_retries=2)
def collect_platform_data(
    self,
    task_id: str,
    platform: str,
    keyword: str,
    limit: int,
    language: str,
    platform_config: dict,
):
    """采集单个平台并落库"""
    db = SessionLocal()
    try:
        task_uuid = UUID(task_id)
        items = _collect_single_platform_sync(
            keyword=keyword,
            limit=limit,
            language=language,
            platform=platform,
            platform_config=platform_config or {},
        )
        _save_raw_data(db, task_uuid, items)
        return {"platform": platform, "count": len(items)}
    except Exception as exc:
        logger.error("Collect platform failed: %s -> %s", platform, exc)
        return {"platform": platform, "count": 0, "error": str(exc)}
    finally:
        db.close()


@shared_task(bind=True, max_retries=2)
def finalize_collection(self, results: List[dict], task_id: str):
    """汇总采集结果并触发分析"""
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"error": "Task not found"}

        task.progress = 50
        db.commit()

        total_items = db.query(RawData).filter(RawData.task_id == task.id).count()
        if total_items == 0:
            task.status = TaskStatus.FAILED
            task.error_message = "No data collected"
            db.commit()
            return {"status": "no_data"}

        from app.workers.analyze_tasks import analyze_task
        analysis_task_id = _dispatch_analyze_task(analyze_task, task_id)
        return {
            "status": "collecting_done",
            "items_count": total_items,
            "analysis_task_id": analysis_task_id,
        }
    except Exception as exc:
        logger.error("Finalize collection failed: %s", exc)
        return {"error": str(exc)}
    finally:
        db.close()


def _save_raw_data(db: Session, task_id: str, items: List[CollectedItem]):
    """保存原始数据到数据库"""
    if not items:
        return

    seen_keys = set()
    unique_items: List[tuple[CollectedItem, Platform]] = []
    for item in items:
        if not item.source_id:
            continue
        try:
            platform = Platform(item.platform)
        except ValueError:
            continue
        key = (platform, item.source_id)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique_items.append((item, platform))

    if not unique_items:
        return

    existing_keys = set()
    platform_to_ids: dict[Platform, set[str]] = {}
    for item, platform in unique_items:
        platform_to_ids.setdefault(platform, set()).add(item.source_id)

    for platform, source_ids in platform_to_ids.items():
        if not source_ids:
            continue
        rows = (
            db.query(RawData.source_id)
            .filter(
                RawData.task_id == task_id,
                RawData.platform == platform,
                RawData.source_id.in_(list(source_ids)),
            )
            .all()
        )
        for (source_id,) in rows:
            existing_keys.add((platform, source_id))

    for item, platform in unique_items:
        key = (platform, item.source_id)
        if key in existing_keys:
            continue
        raw_data = RawData(
            task_id=task_id,
            platform=platform,
            content_type=ContentType(item.content_type),
            source_id=item.source_id,
            title=item.title,
            content=item.content,
            author=item.author,
            url=item.url,
            metrics=item.metrics,
            extra_fields=item.extra_fields,
            published_at=item.published_at,
        )
        db.add(raw_data)

    db.commit()


def _dispatch_analyze_task(
    analyze_task,
    task_id: str,
    max_retries: int = 3,
    base_delay: float = 2.0,
):
    """Dispatch analyze task with retries for transient broker issues."""
    for attempt in range(1, max_retries + 1):
        try:
            result = analyze_task.delay(task_id)
            logger.info("Dispatched analyze task: %s -> %s", task_id, result.id)
            return result.id
        except (OperationalError, CeleryError, ConnectionError, OSError) as exc:
            if attempt >= max_retries:
                logger.error("Failed to dispatch analyze task after %s attempts: %s", attempt, exc)
                raise
            wait_time = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "Dispatch analyze task failed (attempt %s/%s). Retrying in %.1fs. Error: %s",
                attempt,
                max_retries,
                wait_time,
                exc,
            )
            time.sleep(wait_time)
