"""数据采集器模块"""
from app.collectors.base import BaseCollector, CollectorRegistry, CollectedItem
from app.collectors.reddit import RedditCollector
from app.collectors.x import XCollector
from app.collectors.youtube import YouTubeCollector

# 注册采集器
CollectorRegistry.register("reddit", RedditCollector)
CollectorRegistry.register("youtube", YouTubeCollector)
CollectorRegistry.register("x", XCollector)

__all__ = [
    "BaseCollector",
    "CollectorRegistry",
    "CollectedItem",
    "RedditCollector",
    "XCollector",
    "YouTubeCollector",
]
