from app.core.config import settings
from app.services.rag import select_contexts


def test_select_contexts_filters_low_relevance() -> None:
    object.__setattr__(settings, "min_relevance", 0.18)
    object.__setattr__(settings, "context_top_k", 5)
    ranked = [
        {"id": "relevant", "rerank_score": 0.99},
        {"id": "noise", "rerank_score": 0.09},
    ]

    assert [item["id"] for item in select_contexts(ranked)] == ["relevant"]

