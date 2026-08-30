from app.services.embeddings import EmbeddingService, cosine_similarity


def test_hash_embedding_is_normalized_and_deterministic() -> None:
    service = EmbeddingService()
    service._load_model = lambda: None
    first = service.encode(["差旅报销标准"])[0]
    second = service.encode(["差旅报销标准"])[0]

    assert first == second
    assert len(first) == 512
    assert cosine_similarity(first, second) > 0.99

