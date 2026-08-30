from __future__ import annotations

import re
from typing import Any

from app.core.config import settings


class RerankerService:
    def __init__(self) -> None:
        self._model = None
        self.mode = "hybrid-demo"
        self.detail = "使用词项覆盖率与向量分数组合排序"

    def _load_model(self) -> None:
        if self._model is not None or settings.model_mode == "demo":
            return
        try:
            from sentence_transformers import CrossEncoder

            kwargs = {}
            if settings.model_mode == "auto":
                kwargs["local_files_only"] = True
            self._model = CrossEncoder(settings.reranker_model, **kwargs)
            self.mode = "bge-reranker-v2-m3"
            self.detail = settings.reranker_model
        except Exception:
            self._model = None

    def rerank(self, question: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._load_model()
        if not candidates:
            return []
        if self._model is not None:
            pairs = [(question, candidate["content"]) for candidate in candidates]
            scores = self._model.predict(pairs, show_progress_bar=False)
            for candidate, score in zip(candidates, scores, strict=True):
                candidate["rerank_score"] = float(score)
        else:
            for candidate in candidates:
                lexical = _lexical_overlap(question, candidate["content"])
                vector_score = max(0.0, float(candidate.get("vector_score", 0.0)))
                candidate["rerank_score"] = 0.55 * lexical + 0.45 * vector_score
        ranked = sorted(candidates, key=lambda item: item["rerank_score"], reverse=True)
        for index, item in enumerate(ranked, start=1):
            item["rerank_rank"] = index
        return ranked


def _lexical_overlap(question: str, content: str) -> float:
    question_tokens = _tokens(question)
    content_tokens = _tokens(content)
    if not question_tokens:
        return 0.0
    weighted_hits = sum(1.0 for token in question_tokens if token in content_tokens)
    return weighted_hits / len(question_tokens)


def _tokens(text: str) -> set[str]:
    compact = re.sub(r"\s+", "", text.lower())
    tokens = set(compact)
    tokens.update(compact[index : index + 2] for index in range(len(compact) - 1))
    tokens.update(re.findall(r"[a-z0-9_]{2,}", text.lower()))
    return tokens


reranker_service = RerankerService()

