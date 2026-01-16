"""情感分析器"""
from typing import List, Dict, Any

from app.analyzers.llm_client import LLMClient
from app.analyzers.llm_validators import validate_sentiment_response
from app.collectors.base import CollectedItem
from prompts.analysis_prompts import (
    SENTIMENT_SYSTEM_PROMPT,
    SENTIMENT_REPAIR_SYSTEM_PROMPT,
    build_sentiment_user_prompt,
    build_sentiment_repair_prompt,
)


class SentimentAnalyzer:
    """情感分析器，使用LLM进行情感打分"""

    def __init__(self):
        self.llm = LLMClient()

    async def analyze_batch(
        self,
        items: List[CollectedItem],
        keyword: str,
        batch_size: int = 10,
    ) -> List[Dict[str, Any]]:
        results = []

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = await self._analyze_single_batch(batch, keyword)
            results.extend(batch_results)

        return results

    async def _analyze_single_batch(self, items: List[CollectedItem], keyword: str) -> List[Dict[str, Any]]:
        texts = []
        for idx, item in enumerate(items):
            text = item.content or item.title or ""
            if len(text) > 500:
                text = text[:500] + "..."
            texts.append(f"[{idx + 1}] {text}")

        prompt = build_sentiment_user_prompt(texts, keyword)

        try:
            response = await self.llm.analyze_json_with_repair(
                prompt=prompt,
                system_prompt=SENTIMENT_SYSTEM_PROMPT,
                repair_system_prompt=SENTIMENT_REPAIR_SYSTEM_PROMPT,
                repair_user_prompt_builder=build_sentiment_repair_prompt,
                validator=lambda data: validate_sentiment_response(data, len(texts)),
            )
            scores_data = response.get("scores", [])
            if not isinstance(scores_data, list):
                scores_data = []

            index_map = {}
            for entry in scores_data:
                if not isinstance(entry, dict):
                    continue
                idx = entry.get("index")
                if isinstance(idx, int):
                    index_map[idx] = entry

            results = []
            for idx, item in enumerate(items, start=1):
                score_info = index_map.get(idx)
                if score_info is None and idx - 1 < len(scores_data):
                    candidate = scores_data[idx - 1]
                    score_info = candidate if isinstance(candidate, dict) else {}
                if score_info is None:
                    score_info = {}
                results.append({
                    "source_id": item.source_id,
                    "score": score_info.get("score", 50),
                    "key_phrases": score_info.get("key_phrases", []),
                    "platform": item.platform,
                    "engagement": item.metrics.get("upvotes", 0) + item.metrics.get("likes", 0),
                })
            return results

        except Exception:
            return [{"source_id": item.source_id, "score": 50, "key_phrases": [], "platform": item.platform, "engagement": 0} for item in items]

    def calculate_weighted_score(self, results: List[Dict[str, Any]]) -> int:
        if not results:
            return 50

        total_weight = 0
        weighted_sum = 0

        for r in results:
            weight = max(1, r.get("engagement", 0) // 10 + 1)
            weighted_sum += r["score"] * weight
            total_weight += weight

        return round(weighted_sum / total_weight) if total_weight > 0 else 50
