from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.core.database import connect, deserialize_embedding
from app.services.embeddings import cosine_similarity


class VectorStore:
    def __init__(self) -> None:
        self._collection = None
        self.mode = "sqlite"
        if settings.vector_store == "sqlite":
            return
        try:
            import chromadb

            client = chromadb.PersistentClient(path=str(settings.chroma_dir))
            self._collection = client.get_or_create_collection(
                name="enterprise_documents", metadata={"hnsw:space": "cosine"}
            )
            self.mode = "chroma"
        except Exception:
            self._collection = None

    def upsert(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        if self._collection is None or not ids:
            return
        self._collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def delete_document(self, document_id: str) -> None:
        if self._collection is not None:
            self._collection.delete(where={"document_id": document_id})

    def query(self, embedding: list[float], top_k: int) -> list[dict[str, Any]]:
        if self._collection is not None and self._collection.count() > 0:
            result = self._collection.query(
                query_embeddings=[embedding],
                n_results=min(top_k, self._collection.count()),
                include=["distances"],
            )
            ids = result.get("ids", [[]])[0]
            distances = result.get("distances", [[]])[0]
            if ids:
                return self._load_rows(ids, [max(0.0, 1.0 - value) for value in distances])
        return self._query_sqlite(embedding, top_k)

    def _query_sqlite(self, embedding: list[float], top_k: int) -> list[dict[str, Any]]:
        with connect() as db:
            rows = db.execute(
                """
                SELECT c.*, d.name AS file_name
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE d.status = 'ready'
                """
            ).fetchall()
        scored = []
        for row in rows:
            item = dict(row)
            item["vector_score"] = cosine_similarity(
                embedding, deserialize_embedding(item.pop("embedding"))
            )
            scored.append(item)
        return sorted(scored, key=lambda item: item["vector_score"], reverse=True)[:top_k]

    def _load_rows(self, ids: list[str], scores: list[float]) -> list[dict[str, Any]]:
        placeholders = ",".join("?" for _ in ids)
        with connect() as db:
            rows = db.execute(
                f"""
                SELECT c.*, d.name AS file_name
                FROM chunks c JOIN documents d ON d.id = c.document_id
                WHERE c.id IN ({placeholders})
                """,
                ids,
            ).fetchall()
        by_id = {row["id"]: dict(row) for row in rows}
        result = []
        for chunk_id, score in zip(ids, scores, strict=True):
            if chunk_id in by_id:
                item = by_id[chunk_id]
                item.pop("embedding", None)
                item["vector_score"] = score
                result.append(item)
        return result


vector_store = VectorStore()

