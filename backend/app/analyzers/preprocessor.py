"""数据预处理器，过滤脏数据"""
import re
from typing import List, Optional

from langdetect import detect, LangDetectException

from app.collectors.base import CollectedItem


class DataPreprocessor:
    """数据预处理器"""

    AD_PATTERNS = [
        r"buy\s+now", r"click\s+here", r"limited\s+offer",
        r"subscribe\s+to", r"follow\s+me", r"check\s+out\s+my",
        r"promo\s*code", r"discount", r"free\s+shipping",
    ]

    BOT_PATTERNS = [r"bot$", r"automoderator", r"^auto", r"_bot$"]

    def __init__(
        self,
        min_length: int = 10,
        max_length: int = 5000,
        target_language: str = "en",
        filter_ads: bool = True,
        filter_bots: bool = True,
    ):
        self.min_length = min_length
        self.max_length = max_length
        self.target_language = target_language
        self.filter_ads = filter_ads
        self.filter_bots = filter_bots

        self.ad_regex = re.compile("|".join(self.AD_PATTERNS), re.IGNORECASE)
        self.bot_regex = re.compile("|".join(self.BOT_PATTERNS), re.IGNORECASE)

    def preprocess(self, items: List[CollectedItem]) -> List[CollectedItem]:
        result = []
        seen_ids = set()

        for item in items:
            if item.source_id in seen_ids:
                continue
            if not self._is_valid(item):
                continue

            seen_ids.add(item.source_id)
            result.append(item)

        result.sort(key=self._get_engagement_score, reverse=True)
        return result

    def _is_valid(self, item: CollectedItem) -> bool:
        text = item.content or item.title or ""

        if len(text) < self.min_length or len(text) > self.max_length:
            return False

        if self.filter_bots and item.author:
            if self.bot_regex.search(item.author):
                return False

        if self.filter_ads and self.ad_regex.search(text):
            return False

        if len(text) > 50:
            try:
                detected_lang = detect(text)
                if self.target_language == "en" and detected_lang not in ["en"]:
                    return False
                if self.target_language == "zh" and detected_lang not in ["zh-cn", "zh-tw", "zh"]:
                    return False
            except LangDetectException:
                pass

        return True

    def _get_engagement_score(self, item: CollectedItem) -> int:
        metrics = item.metrics or {}
        score = metrics.get("upvotes", 0) + metrics.get("num_comments", 0) * 2
        score += metrics.get("views", 0) // 1000 + metrics.get("likes", 0) * 10
        return score

    def extract_top_items(
        self,
        items: List[CollectedItem],
        limit: int = 50,
        min_engagement: int = 5,
        ensure_platform_balance: bool = True,
    ) -> List[CollectedItem]:
        filtered = [item for item in items if self._get_engagement_score(item) >= min_engagement]
        if not ensure_platform_balance:
            return filtered[:limit]
        if not items:
            return []

        by_platform = {}
        for item in items:
            by_platform.setdefault(item.platform, []).append(item)

        for platform_items in by_platform.values():
            platform_items.sort(key=self._get_engagement_score, reverse=True)

        per_platform = max(1, limit // max(len(by_platform), 1))
        selected: List[CollectedItem] = []
        for platform_items in by_platform.values():
            platform_filtered = [
                item for item in platform_items
                if self._get_engagement_score(item) >= min_engagement
            ]
            if not platform_filtered:
                platform_filtered = platform_items
            selected.extend(platform_filtered[:per_platform])

        if len(selected) < limit:
            remaining = []
            for platform_items in by_platform.values():
                remaining.extend(platform_items[per_platform:])
            remaining.sort(key=self._get_engagement_score, reverse=True)
            selected.extend(remaining[: max(0, limit - len(selected))])

        return selected[:limit]
