from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence

from app.core.config import settings


class EmbeddingService:
    dimension = 512

    def __init__(self) -> None:
        self._model = None
        self.mode = "hash-demo"
        self.detail = "使用 512 维本地哈希嵌入；安装 ML 依赖并启用模型后切换 BGE"

    def _load_model(self) -> None:
        if self._model is not None or settings.model_mode == "demo":
            return
        try:
            from sentence_transformers import SentenceTransformer

            kwargs = {}
            if settings.model_mode == "auto":
                kwargs["local_files_only"] = True
            self._model = SentenceTransformer(settings.embedding_model, **kwargs)
            self.dimension = int(self._model.get_sentence_embedding_dimension())
            self.mode = "bge-small-zh-v1.5"
            self.detail = settings.embedding_model
        except Exception:
            self._model = None

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        self._load_model()
        if self._model is not None:
            values = self._model.encode(
                list(texts), normalize_embeddings=True, show_progress_bar=False
            )
            return [[float(item) for item in row] for row in values]
        return [self._hash_embedding(text) for text in texts]

    def _hash_embedding(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        normalized = re.sub(r"\s+", "", text.lower())
        tokens = list(normalized)
        tokens.extend(normalized[index : index + 2] for index in range(len(normalized) - 1))
        tokens.extend(re.findall(r"[a-z0-9_]+", text.lower()))
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            raw = int.from_bytes(digest, "big")
            index = raw % self.dimension
            vector[index] += 1.0 if raw & 1 else -1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


embedding_service = EmbeddingService()


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True))

