"""Validation helpers for LLM outputs."""
import re
from typing import Any, Dict, List, Tuple


def validate_sentiment_response(data: Any, expected_count: int) -> Tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "Root must be an object."
    scores = data.get("scores")
    if not isinstance(scores, list):
        return False, '"scores" must be a list.'
    if len(scores) != expected_count:
        return False, f'"scores" must contain exactly {expected_count} items.'
    for i, item in enumerate(scores, start=1):
        if not isinstance(item, dict):
            return False, f"Item {i} must be an object."
        index = item.get("index")
        if not isinstance(index, int) or index != i:
            return False, f'Item {i} must have "index" == {i}.'
        score = item.get("score")
        if not isinstance(score, int) or not (0 <= score <= 100):
            return False, f'Item {i} must have integer "score" in [0,100].'
        key_phrases = item.get("key_phrases")
        if not isinstance(key_phrases, list):
            return False, f'Item {i} must have "key_phrases" list.'
        if len(key_phrases) > 3:
            return False, f'Item {i} has too many key phrases.'
        for phrase in key_phrases:
            if not isinstance(phrase, str):
                return False, f'Item {i} has a non-string key phrase.'
    return True, ""


def validate_clustering_response(
    data: Any,
    expected_count: int | None = None,
    min_count: int = 2,
    max_count: int = 6,
) -> Tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "Root must be an object."
    key_opinions = data.get("key_opinions")
    summary = data.get("summary")
    if not isinstance(key_opinions, list):
        return False, '"key_opinions" must be a list.'
    if expected_count is not None:
        if len(key_opinions) != expected_count:
            return False, f'"key_opinions" must contain exactly {expected_count} items.'
    else:
        if not (min_count <= len(key_opinions) <= max_count):
            return False, f'"key_opinions" must contain between {min_count} and {max_count} items.'
    for idx, item in enumerate(key_opinions, start=1):
        if not isinstance(item, dict):
            return False, f"Opinion {idx} must be an object."
        title = item.get("title")
        description = item.get("description")
        points = item.get("points", [])
        if not isinstance(title, str) or not title.strip():
            return False, f"Opinion {idx} must have non-empty title."
        if not isinstance(description, str) or not description.strip():
            return False, f"Opinion {idx} must have non-empty description."
        if points is not None:
            if not isinstance(points, list):
                return False, f'Opinion {idx} "points" must be a list.'
            for point in points:
                if not isinstance(point, str):
                    return False, f'Opinion {idx} has a non-string point.'
    if not isinstance(summary, str) or not summary.strip():
        return False, '"summary" must be a non-empty string.'
    sentence_markers = re.findall(r"[.!?。！？]", summary)
    if len(sentence_markers) < 3 and len(summary.strip()) < 180:
        return False, '"summary" is too short; expected 4-6 sentences.'
    return True, ""


def validate_mermaid_output(code: str) -> Tuple[bool, str]:
    if not isinstance(code, str):
        return False, "Mermaid output must be a string."
    lines = [line.rstrip() for line in code.splitlines() if line.strip()]
    if not lines:
        return False, "Mermaid output is empty."
    if lines[0].strip() != "mindmap":
        return False, 'First line must be "mindmap".'
    root_lines = [line for line in lines if line.startswith("  ") and line.strip().startswith("root((")]
    if len(root_lines) != 1:
        return False, 'Expected exactly one root node "root((keyword))".'

    sentiment_lines = [line for line in lines if line.startswith("    ") and line.strip() == "Sentiment"]
    if len(sentiment_lines) != 1:
        return False, 'Expected a "Sentiment" branch under root.'

    sentiment_label = [
        line for line in lines
        if line.startswith("      ") and not line.strip().startswith("root((")
    ]
    if not sentiment_label:
        return False, 'Expected a sentiment label under "Sentiment".'

    opinion_lines: List[str] = []
    for line in lines:
        if line.startswith("    ") and not line.startswith("      "):
            label = line.strip()
            if label != "Sentiment":
                opinion_lines.append(label)
    if len(opinion_lines) < 2:
        return False, "Expected at least 2 opinion branches under root."
    return True, ""
