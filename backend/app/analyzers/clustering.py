"""观点聚类和摘要生成"""
import re
from typing import List, Dict, Any

from app.analyzers.llm_client import LLMClient
from app.analyzers.llm_validators import validate_clustering_response
from app.config import get_settings
from prompts.analysis_prompts import (
    CLUSTERING_SYSTEM_PROMPT,
    CLUSTERING_REPAIR_SYSTEM_PROMPT,
    build_clustering_user_prompt,
    build_clustering_repair_prompt,
)


class ClusteringAnalyzer:
    """观点聚类和摘要生成器"""

    def __init__(self):
        self.llm = LLMClient()

    def _normalize_key_opinions(self, key_opinions: Any) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        if isinstance(key_opinions, str):
            key_opinions = [key_opinions]
        if not isinstance(key_opinions, list):
            return normalized
        for item in key_opinions:
            if isinstance(item, dict):
                title = str(item.get("title", "")).strip()
                description = str(item.get("description", "")).strip()
                points = item.get("points", [])
                points = self._normalize_points(points, description)
                if title or description:
                    normalized.append({
                        "title": title or "观点",
                        "description": description or "",
                        "points": points,
                    })
            elif isinstance(item, str):
                text = item.strip()
                if text:
                    normalized.append({
                        "title": text,
                        "description": "",
                        "points": self._normalize_points([], text),
                    })
        return normalized

    def _normalize_points(self, points: Any, fallback_text: str) -> List[str]:
        if isinstance(points, list):
            cleaned = [self._sanitize_point(p) for p in points if isinstance(p, str)]
            cleaned = [p for p in cleaned if p]
        else:
            cleaned = []

        if cleaned:
            return cleaned[:4]

        return self._extract_points(fallback_text)

    def _extract_points(self, text: str, max_points: int = 3) -> List[str]:
        if not isinstance(text, str):
            return []
        parts = re.split(r"[。.!?;；，,、]+", text)
        cleaned = [self._sanitize_point(p) for p in parts if p.strip()]
        cleaned = [p for p in cleaned if p]
        if cleaned:
            return cleaned[:max_points]
        fallback = self._sanitize_point(text)
        return [fallback] if fallback else []

    def _sanitize_point(self, text: str, max_len: int = 80) -> str:
        if not isinstance(text, str):
            return ""
        cleaned = " ".join(text.replace("\n", " ").replace("\r", " ").split())
        cleaned = cleaned.strip()
        if not cleaned:
            return ""
        return cleaned[:max_len]

    def _determine_target_count(self, item_count: int) -> int:
        settings = get_settings()
        min_count = max(1, settings.opinion_count_min)
        max_count = max(min_count, settings.opinion_count_max)
        thresholds = self._parse_thresholds(settings.opinion_count_thresholds)

        if not thresholds:
            return max(min_count, min(max_count, 3))

        count = min_count
        for threshold in thresholds:
            if item_count <= threshold:
                return min(count, max_count)
            count += 1
        return max_count

    def _parse_thresholds(self, raw: str) -> List[int]:
        if not isinstance(raw, str):
            return []
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        values = []
        for part in parts:
            try:
                value = int(part)
            except ValueError:
                continue
            if value > 0:
                values.append(value)
        return sorted(set(values))

    async def analyze(
        self,
        sentiment_results: List[Dict[str, Any]],
        items_text: List[str],
        keyword: str,
        report_language: str = "auto",
    ) -> Dict[str, Any]:
        report_language = (report_language or "auto").strip()
        if not report_language:
            report_language = "auto"
        all_phrases = []
        for r in sentiment_results:
            all_phrases.extend(r.get("key_phrases", []))

        positive_count = len([r for r in sentiment_results if r['score'] >= 60])
        neutral_count = len([r for r in sentiment_results if 40 <= r['score'] < 60])
        negative_count = len([r for r in sentiment_results if r['score'] < 40])

        target_count = self._determine_target_count(len(items_text))
        prompt = build_clustering_user_prompt(
            keyword=keyword,
            items_text=items_text,
            all_phrases=all_phrases,
            positive_count=positive_count,
            neutral_count=neutral_count,
            negative_count=negative_count,
            target_count=target_count,
            report_language=report_language,
        )

        try:
            response = await self.llm.analyze_json_with_repair(
                prompt=prompt,
                system_prompt=CLUSTERING_SYSTEM_PROMPT,
                repair_system_prompt=CLUSTERING_REPAIR_SYSTEM_PROMPT,
                repair_user_prompt_builder=build_clustering_repair_prompt,
                validator=lambda data: validate_clustering_response(
                    data,
                    expected_count=target_count,
                ),
            )
            key_opinions = self._normalize_key_opinions(response.get("key_opinions", []))
            return {
                "key_opinions": key_opinions,
                "summary": response.get("summary", f"Analysis of {keyword} unavailable."),
            }
        except Exception:
            return {
                "key_opinions": [{"title": "Analysis Error", "description": "Unable to cluster opinions."}],
                "summary": f"Unable to generate summary for {keyword}.",
            }
