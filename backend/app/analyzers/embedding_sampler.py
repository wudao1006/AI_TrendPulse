"""Semantic sampling with local embeddings."""
from __future__ import annotations

import math
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans

from app.collectors.base import CollectedItem


class EmbeddingSampler:
    """Sample representative items with local embeddings."""

    _model_cache: dict[str, SentenceTransformer] = {}

    def __init__(
        self,
        model_name: str,
        max_items: int = 200,
        target_count: int = 50,
        k_min: int = 3,
        k_max: int = 10,
        outlier_ratio: float = 0.1,
        batch_size: int = 64,
        text_max_length: int = 400,
    ) -> None:
        if model_name not in self._model_cache:
            self._model_cache[model_name] = SentenceTransformer(model_name)
        self.model = self._model_cache[model_name]
        self.max_items = max(1, max_items)
        self.target_count = max(1, target_count)
        self.k_min = max(1, k_min)
        self.k_max = max(self.k_min, k_max)
        self.outlier_ratio = max(0.0, min(outlier_ratio, 0.5))
        self.batch_size = max(1, batch_size)
        self.text_max_length = max(50, text_max_length)

    def sample(self, items: List[CollectedItem]) -> List[CollectedItem]:
        if not items:
            return []

        candidates = items[: self.max_items]
        target_count = min(self.target_count, len(candidates))
        if len(candidates) <= target_count:
            return candidates

        texts = [self._build_text(item) for item in candidates]
        embeddings = self._encode(texts)
        if embeddings is None or len(embeddings) != len(candidates):
            return candidates[:target_count]

        selected_indices = self._cluster_and_select(embeddings, target_count)
        if not selected_indices:
            return candidates[:target_count]

        selected_indices = sorted(selected_indices)
        return [candidates[i] for i in selected_indices]

    def _build_text(self, item: CollectedItem) -> str:
        text = item.content or item.title or ""
        text = " ".join(text.replace("\n", " ").replace("\r", " ").split())
        if len(text) > self.text_max_length:
            text = text[: self.text_max_length]
        return text

    def _encode(self, texts: List[str]) -> np.ndarray | None:
        if not texts:
            return None
        return self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

    def _cluster_and_select(self, embeddings: np.ndarray, target_count: int) -> List[int]:
        n = embeddings.shape[0]
        if n <= target_count:
            return list(range(n))

        k = int(math.sqrt(n))
        k = min(self.k_max, max(self.k_min, k))
        if k >= n:
            return list(range(target_count))

        kmeans = KMeans(n_clusters=k, n_init="auto", random_state=42)
        labels = kmeans.fit_predict(embeddings)
        centers = kmeans.cluster_centers_
        centers = centers / np.linalg.norm(centers, axis=1, keepdims=True)
        distances = 1 - np.sum(embeddings * centers[labels], axis=1)

        cluster_indices: dict[int, List[int]] = {}
        for idx, label in enumerate(labels):
            cluster_indices.setdefault(int(label), []).append(idx)

        cluster_sizes = {k: len(v) for k, v in cluster_indices.items()}
        desired = {
            k: max(1, round(target_count * size / n))
            for k, size in cluster_sizes.items()
        }

        total_desired = sum(desired.values())
        if total_desired > target_count:
            for k in sorted(desired, key=lambda x: cluster_sizes[x], reverse=True):
                if total_desired <= target_count:
                    break
                if desired[k] > 1:
                    desired[k] -= 1
                    total_desired -= 1

        selected = set()
        for label, idxs in cluster_indices.items():
            idxs_sorted = sorted(idxs, key=lambda i: distances[i])
            take = min(desired.get(label, 1), len(idxs_sorted))
            selected.update(idxs_sorted[:take])

        outlier_count = int(target_count * self.outlier_ratio)
        outlier_count = min(outlier_count, target_count)
        outliers = []
        if outlier_count > 0:
            for idx in np.argsort(distances)[::-1]:
                if idx not in selected:
                    outliers.append(int(idx))
                    if len(outliers) >= outlier_count:
                        break
            selected.update(outliers)

        if len(selected) > target_count:
            outlier_set = set(outliers)
            candidates = [i for i in selected if i not in outlier_set]
            candidates_sorted = sorted(candidates, key=lambda i: distances[i])
            while len(selected) > target_count and candidates_sorted:
                selected.remove(candidates_sorted.pop(0))

        if len(selected) < target_count:
            for idx in np.argsort(distances):
                if idx not in selected:
                    selected.add(int(idx))
                    if len(selected) >= target_count:
                        break

        return list(selected)[:target_count]
