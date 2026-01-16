"""采集器基类和注册机制"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Type


@dataclass
class CollectedItem:
    """采集到的数据项"""
    platform: str
    content_type: str
    source_id: str
    title: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None
    url: Optional[str] = None
    metrics: Dict = field(default_factory=dict)
    extra_fields: Dict = field(default_factory=dict)
    published_at: Optional[datetime] = None


class BaseCollector(ABC):
    """采集器基类"""

    platform_name: str = ""

    def __init__(self, config: Dict = None):
        self.config = config or {}

    @abstractmethod
    async def collect(
        self,
        keyword: str,
        limit: int = 50,
        language: str = "en",
    ) -> List[CollectedItem]:
        pass

    def clean_text(self, text: Optional[str]) -> Optional[str]:
        if not text:
            return None
        text = text.strip()
        if len(text) < 10:
            return None
        return text

    def is_valid_item(self, item: CollectedItem) -> bool:
        return bool(item.title or item.content)


class CollectorRegistry:
    """采集器注册表"""

    _collectors: Dict[str, Type[BaseCollector]] = {}

    @classmethod
    def register(cls, platform: str, collector_class: Type[BaseCollector]):
        cls._collectors[platform] = collector_class

    @classmethod
    def get(cls, platform: str) -> Optional[Type[BaseCollector]]:
        return cls._collectors.get(platform)

    @classmethod
    def get_instance(cls, platform: str, config: Dict = None) -> Optional[BaseCollector]:
        collector_class = cls.get(platform)
        if collector_class:
            return collector_class(config)
        return None

    @classmethod
    def list_platforms(cls) -> List[str]:
        return list(cls._collectors.keys())
