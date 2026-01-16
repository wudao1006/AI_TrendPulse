"""AI分析任务"""
import asyncio
import heapq
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone

from celery import shared_task

from app.database import SessionLocal
from app.models import Task, TaskStatus, RawData, AnalysisResult, Alert
from app.collectors.base import CollectedItem
from app.analyzers import (
    DataPreprocessor,
    SentimentAnalyzer,
    ClusteringAnalyzer,
    MermaidGenerator,
)
from app.analyzers.embedding_sampler import EmbeddingSampler
from app.config import get_settings


@shared_task(bind=True, max_retries=2)
def analyze_task(self, task_id: str):
    """执行AI分析"""
    db = SessionLocal()

    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"error": "Task not found"}

        settings = get_settings()
        report_lang = task.report_language or "en"
        # 确保预处理器使用任务指定的语言，避免误过滤中文等非英文内容
        preprocessor = DataPreprocessor(target_language=report_lang if report_lang != "auto" else "en")
        analysis_candidate_limit = settings.semantic_sampling_max_items
        candidate_heaps: dict[str, list[tuple[int, int, CollectedItem]]] = defaultdict(list)
        heap_counter = 0

        total = 0
        platform_counts = Counter()
        platform_set = set()
        engagements: list[float] = []
        total_engagement = 0.0
        now = datetime.now(timezone.utc)
        half_life_hours = 24.0
        decay_lambda = math.log(2) / half_life_hours

        raw_query = (
            db.query(RawData)
            .filter(RawData.task_id == task_id)
            .yield_per(500)
        )

        for r in raw_query:
            total += 1
            platform_value = r.platform.value
            platform_counts[platform_value] += 1
            platform_set.add(platform_value)

            weighted_engagement = _weighted_engagement_from_metrics(
                r.metrics or {},
                r.published_at,
                now,
                decay_lambda,
            )
            engagements.append(weighted_engagement)
            total_engagement += weighted_engagement

            item = CollectedItem(
                platform=platform_value,
                content_type=r.content_type.value,
                source_id=r.source_id,
                title=r.title,
                content=r.content,
                author=r.author,
                url=r.url,
                metrics=r.metrics or {},
                extra_fields=r.extra_fields or {},
                published_at=r.published_at,
            )

            if not preprocessor._is_valid(item):
                continue

            score = preprocessor._get_engagement_score(item)
            heap = candidate_heaps[platform_value]
            heap_counter += 1
            if len(heap) < analysis_candidate_limit:
                heapq.heappush(heap, (score, heap_counter, item))
            elif score > heap[0][0]:
                heapq.heapreplace(heap, (score, heap_counter, item))

        if total == 0:
            task.status = TaskStatus.FAILED
            task.error_message = "No data collected"
            db.commit()
            return {"error": "No data"}

        items = []
        for heap in candidate_heaps.values():
            items.extend(item for _, _, item in heap)
        if not items:
            task.status = TaskStatus.FAILED
            task.error_message = "No valid data for analysis"
            db.commit()
            return {"error": "No valid data"}

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                _run_analysis(
                    task.keyword,
                    items,
                    task.report_language or "auto",
                    task.semantic_sampling,
                )
            )
        finally:
            loop.close()

        platform_distribution = {
            p: round(c / total * 100) for p, c in platform_counts.items()
        }

        heat_index = _calculate_heat_index_from_stats(
            engagements,
            total_engagement,
            total,
            platform_set,
            expected_count=task.limit_count,
            expected_platforms=task.platforms,
        )

        analysis_result = db.query(AnalysisResult).filter(
            AnalysisResult.task_id == task_id
        ).first()

        if analysis_result:
            analysis_result.sentiment_score = result["sentiment_score"]
            analysis_result.key_opinions = result["key_opinions"]
            analysis_result.summary = result["summary"]
            analysis_result.mermaid_code = result["mermaid_code"]
            analysis_result.heat_index = heat_index
            analysis_result.total_items = total
            analysis_result.platform_distribution = platform_distribution
            analysis_result.analyzed_at = datetime.utcnow()
        else:
            analysis_result = AnalysisResult(
                task_id=task_id,
                sentiment_score=result["sentiment_score"],
                key_opinions=result["key_opinions"],
                summary=result["summary"],
                mermaid_code=result["mermaid_code"],
                heat_index=heat_index,
                total_items=total,
                platform_distribution=platform_distribution,
            )
            db.add(analysis_result)

        task.status = TaskStatus.COMPLETED
        task.progress = 100
        db.commit()

        _check_and_create_alert(db, task_id, result["sentiment_score"])

        return {"status": "completed", "sentiment_score": result["sentiment_score"]}

    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        db.commit()
        raise
    finally:
        db.close()


async def _run_analysis(
    keyword: str,
    items: list,
    report_language: str,
    semantic_sampling: bool,
) -> dict:
    """执行完整分析流程"""
    preprocessor = DataPreprocessor(target_language=report_language if report_language != "auto" else "en")
    cleaned_items = preprocessor.preprocess(items)
    settings = get_settings()
    if semantic_sampling:
        candidate_items = preprocessor.extract_top_items(
            cleaned_items,
            limit=settings.semantic_sampling_max_items,
            ensure_platform_balance=True,
        )
        sampler = EmbeddingSampler(
            model_name=settings.semantic_sampling_model,
            max_items=settings.semantic_sampling_max_items,
            target_count=settings.semantic_sampling_target_count,
            k_min=settings.semantic_sampling_k_min,
            k_max=settings.semantic_sampling_k_max,
            outlier_ratio=settings.semantic_sampling_outlier_ratio,
            batch_size=settings.semantic_sampling_batch_size,
            text_max_length=settings.semantic_sampling_text_max_length,
        )
        top_items = sampler.sample(candidate_items)
    else:
        top_items = preprocessor.extract_top_items(
            cleaned_items,
            limit=50,
            ensure_platform_balance=True,
        )

    sentiment_analyzer = SentimentAnalyzer()
    sentiment_results = await sentiment_analyzer.analyze_batch(top_items, keyword)

    sentiment_score = sentiment_analyzer.calculate_weighted_score(sentiment_results)

    clustering_analyzer = ClusteringAnalyzer()
    trunc_len = settings.analysis_text_truncation_limit
    items_text = [(item.content or item.title or "")[:trunc_len] for item in top_items]
    clustering_result = await clustering_analyzer.analyze(
        sentiment_results,
        items_text,
        keyword,
        report_language=report_language,
    )

    mermaid_generator = MermaidGenerator()
    mermaid_code = await mermaid_generator.generate(keyword, clustering_result["key_opinions"], sentiment_score)

    return {
        "sentiment_score": sentiment_score,
        "key_opinions": clustering_result["key_opinions"],
        "summary": clustering_result["summary"],
        "mermaid_code": mermaid_code,
    }


def _weighted_engagement_from_metrics(
    metrics: dict,
    published_at: datetime | None,
    now: datetime,
    decay_lambda: float,
) -> float:
    upvotes = metrics.get("upvotes", 0)
    likes = metrics.get("likes", 0)
    views = metrics.get("views", 0)
    num_comments = metrics.get("num_comments", 0)

    base_engagement = upvotes + likes + views // 100 + num_comments * 5
    if isinstance(published_at, datetime):
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        age_hours = max(0.0, (now - published_at).total_seconds() / 3600)
        weight = math.exp(-decay_lambda * age_hours)
    else:
        weight = 1.0

    return base_engagement * weight


def _calculate_heat_index_from_stats(
    engagements: list[float],
    total_engagement: float,
    total_items: int,
    platform_set: set[str],
    expected_count: int = 0,
    expected_platforms: list | None = None,
) -> float:
    if not engagements:
        return 0.0

    avg_engagement = total_engagement / max(total_items, 1)
    sorted_engagements = sorted(engagements)
    p90_index = max(0, int(len(sorted_engagements) * 0.9) - 1)
    p90_engagement = sorted_engagements[p90_index]

    scale = math.log1p(1_000_000)
    engagement_score = (
        (math.log1p(max(avg_engagement, 0)) / scale) * 70
        + (math.log1p(max(p90_engagement, 0)) / scale) * 30
    )

    volume_ratio = total_items / max(expected_count, 1) if expected_count else 1.0
    volume_score = min(1.0, volume_ratio) * 100

    expected_platforms = expected_platforms or []
    platform_ratio = (
        len(platform_set) / max(len(expected_platforms), 1)
        if expected_platforms
        else 1.0
    )
    platform_score = min(1.0, platform_ratio) * 100

    heat = 0.6 * min(100.0, engagement_score) + 0.25 * volume_score + 0.15 * platform_score
    return round(min(100.0, heat), 2)

def _calculate_heat_index(
    items: list,
    expected_count: int = 0,
    expected_platforms: list | None = None,
) -> float:
    """计算热度指数"""
    total_engagement = 0
    engagements = []
    platform_set = set()
    now = datetime.now(timezone.utc)
    half_life_hours = 24.0
    decay_lambda = math.log(2) / half_life_hours
    for item in items:
        metrics = item.metrics or {}
        upvotes = metrics.get("upvotes", 0)
        likes = metrics.get("likes", 0)
        views = metrics.get("views", 0)
        num_comments = metrics.get("num_comments", 0)

        base_engagement = upvotes + likes + views // 100 + num_comments * 5
        published_at = getattr(item, "published_at", None)
        if isinstance(published_at, datetime):
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
            age_hours = max(0.0, (now - published_at).total_seconds() / 3600)
            weight = math.exp(-decay_lambda * age_hours)
        else:
            weight = 1.0

        weighted_engagement = base_engagement * weight
        total_engagement += weighted_engagement
        engagements.append(weighted_engagement)
        try:
            platform_set.add(item.platform.value)
        except AttributeError:
            platform_set.add(str(item.platform))

    if not engagements:
        return 0.0

    avg_engagement = total_engagement / max(len(items), 1)
    sorted_engagements = sorted(engagements)
    p90_index = max(0, int(len(sorted_engagements) * 0.9) - 1)
    p90_engagement = sorted_engagements[p90_index]

    scale = math.log1p(1_000_000)
    engagement_score = (
        (math.log1p(max(avg_engagement, 0)) / scale) * 70
        + (math.log1p(max(p90_engagement, 0)) / scale) * 30
    )

    volume_ratio = len(items) / max(expected_count, 1) if expected_count else 1.0
    volume_score = min(1.0, volume_ratio) * 100

    expected_platforms = expected_platforms or []
    platform_ratio = len(platform_set) / max(len(expected_platforms), 1) if expected_platforms else 1.0
    platform_score = min(1.0, platform_ratio) * 100

    heat = 0.6 * min(100.0, engagement_score) + 0.25 * volume_score + 0.15 * platform_score
    return round(min(100.0, heat), 2)


def _check_and_create_alert(db, task_id: str, sentiment_score: int):
    """检查是否需要创建报警"""
    from app.models import Subscription

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return

    subscription = db.query(Subscription).filter(
        Subscription.keyword == task.keyword,
        Subscription.is_active == True,
    ).first()

    if subscription and sentiment_score < subscription.alert_threshold:
        alert = Alert(
            subscription_id=subscription.id,
            task_id=task_id,
            sentiment_score=sentiment_score,
            alert_type="negative_sentiment",
        )
        db.add(alert)
        db.commit()
