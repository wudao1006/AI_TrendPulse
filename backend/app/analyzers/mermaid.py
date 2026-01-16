"""Mermaid思维导图生成器"""
import re
from typing import List, Dict, Any

from app.analyzers.llm_client import LLMClient
from app.analyzers.llm_validators import validate_mermaid_output
from prompts.analysis_prompts import (
    MERMAID_SYSTEM_PROMPT,
    MERMAID_REPAIR_SYSTEM_PROMPT,
    build_mermaid_user_prompt,
    build_mermaid_repair_prompt,
)


class MermaidGenerator:
    """生成Mermaid格式的思维导图"""

    def __init__(self):
        self.llm = LLMClient()

    async def generate(
        self,
        keyword: str,
        key_opinions: List[Dict[str, Any]],
        sentiment_score: int,
    ) -> str:
        sentiment_label = self._get_sentiment_label(sentiment_score)
        safe_opinions = self._normalize_key_opinions(key_opinions)
        opinions_text = "\n".join([
            f"- {op['title']}: {op['description']}\n  points: {', '.join(op.get('points', []))}"
            for op in safe_opinions
        ])
        opinion_count = max(2, min(len(safe_opinions), 6))

        prompt = build_mermaid_user_prompt(
            keyword=keyword,
            opinions_text=opinions_text,
            sentiment_label=sentiment_label,
            sentiment_score=sentiment_score,
            opinion_count=opinion_count,
        )

        try:
            response = await self.llm.chat(
                [
                    {"role": "system", "content": MERMAID_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=1000,
            )
            code = self._extract_mermaid_code(response)
            valid, error = validate_mermaid_output(code)
            if valid:
                return code

            repair_prompt = build_mermaid_repair_prompt(response, error)
            repair_response = await self.llm.chat(
                [
                    {"role": "system", "content": MERMAID_REPAIR_SYSTEM_PROMPT},
                    {"role": "user", "content": repair_prompt},
                ],
                temperature=0.2,
                max_tokens=800,
            )
            repaired_code = self._extract_mermaid_code(repair_response)
            valid, _ = validate_mermaid_output(repaired_code)
            if valid:
                return repaired_code
        except Exception:
            return self._generate_fallback(keyword, safe_opinions, sentiment_label)
        return self._generate_fallback(keyword, safe_opinions, sentiment_label)

    def build_safe_mindmap(
        self,
        keyword: str,
        key_opinions: List[Dict[str, Any]],
        sentiment_score: int,
    ) -> str:
        sentiment_label = self._get_sentiment_label(sentiment_score)
        safe_opinions = self._normalize_key_opinions(key_opinions)
        return self._generate_fallback(keyword, safe_opinions, sentiment_label)

    def _get_sentiment_label(self, score: int) -> str:
        if score >= 80: return "Very Positive"
        elif score >= 60: return "Positive"
        elif score >= 40: return "Neutral"
        elif score >= 20: return "Negative"
        else: return "Very Negative"

    def _sanitize_label(self, label: str, max_len: int = 30) -> str:
        if not isinstance(label, str):
            return "Point"
        cleaned = label.replace("\n", " ").replace("\r", " ").strip()
        for ch in ['"', "'", "(", ")", "[", "]", "{", "}", ":", ";", "|"]:
            cleaned = cleaned.replace(ch, " ")
        cleaned = " ".join(cleaned.split())
        if not cleaned:
            return "Point"
        return cleaned[:max_len]

    def _normalize_key_opinions(self, key_opinions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if isinstance(key_opinions, list):
            normalized: List[Dict[str, Any]] = []
            for item in key_opinions:
                if isinstance(item, dict):
                    title = str(item.get("title", "")).strip()
                    description = str(item.get("description", "")).strip()
                    points = self._normalize_points(item.get("points", []), description)
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
        if isinstance(key_opinions, str) and key_opinions.strip():
            return [{
                "title": key_opinions.strip(),
                "description": "",
                "points": self._normalize_points([], key_opinions.strip()),
            }]
        return []

    def _extract_mermaid_code(self, response: str) -> str:
        if "```mermaid" in response:
            start = response.find("```mermaid") + len("```mermaid")
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()
        if "mindmap" in response:
            return response[response.find("mindmap"):].strip()
        return response.strip()

    def _generate_fallback(self, keyword: str, key_opinions: List[Dict[str, Any]], sentiment_label: str) -> str:
        safe_keyword = self._sanitize_label(keyword, max_len=40)
        lines = [
            "mindmap",
            f"  root(({safe_keyword}))",
            "    Sentiment",
            f"      {self._sanitize_label(sentiment_label, max_len=20)}",
        ]
        for op in key_opinions[:6]:
            title = op.get("title", "Point")
            lines.append(f"    {self._sanitize_label(title, max_len=30)}")
            points = op.get("points") or []
            points = self._normalize_points(points, op.get("description", ""))
            if points:
                lines.append("      Points")
                for point in points[:3]:
                    lines.append(f"        {self._sanitize_label(point, max_len=30)}")
        return "\n".join(lines)

    def _normalize_points(self, points: Any, fallback_text: str) -> List[str]:
        if isinstance(points, list):
            cleaned = [self._sanitize_label(p, max_len=30) for p in points if isinstance(p, str)]
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
        cleaned = [self._sanitize_label(p, max_len=30) for p in parts if p.strip()]
        cleaned = [p for p in cleaned if p]
        if cleaned:
            return cleaned[:max_points]
        fallback = self._sanitize_label(text, max_len=30)
        return [fallback] if fallback else []
