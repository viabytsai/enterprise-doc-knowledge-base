from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.vector_store import vector_store


def test_upload_retrieve_stream_and_delete(tmp_path) -> None:
    object.__setattr__(settings, "data_dir", tmp_path)
    object.__setattr__(settings, "model_mode", "demo")
    object.__setattr__(settings, "vector_store", "sqlite")
    vector_store._collection = None
    vector_store.mode = "sqlite"

    content = "# 差旅制度\n\n## 住宿标准\n\n一线城市住宿上限为每人每晚 600 元。"
    with TestClient(app) as client:
        uploaded = client.post(
            "/api/documents",
            files={"file": ("差旅制度.md", content.encode("utf-8"), "text/markdown")},
        )
        assert uploaded.status_code == 201
        document = uploaded.json()
        assert document["status"] == "ready"
        assert document["chunk_count"] >= 1

        debug = client.post(
            "/api/retrieval/debug",
            json={"question": "一线城市住宿上限是多少？", "top_k": 20},
        )
        assert debug.status_code == 200
        assert "600" in debug.json()["ranked"][0]["content"]

        with client.stream(
            "POST",
            "/api/chat/stream",
            json={"question": "一线城市住宿上限是多少？"},
        ) as streamed:
            body = streamed.read().decode("utf-8")
        assert streamed.status_code == 200
        assert "event: meta" in body
        assert "event: token" in body
        assert "差旅制度.md" in body
        assert "search_knowledge" in body

        removed = client.delete(f"/api/documents/{document['id']}")
        assert removed.status_code == 204
