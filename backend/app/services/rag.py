from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.database import connect, serialize_embedding, utc_now
from app.services.embeddings import embedding_service
from app.services.parser import parse_document, split_pages
from app.services.reranker import reranker_service
from app.services.vector_store import vector_store


def create_document_record(name: str, file_type: str, source_path: Path) -> str:
    document_id = str(uuid.uuid4())
    with connect() as db:
        db.execute(
            """
            INSERT INTO documents
            (id, name, file_type, source_path, status, created_at)
            VALUES (?, ?, ?, ?, 'processing', ?)
            """,
            (document_id, name, file_type, str(source_path), utc_now()),
        )
    return document_id


def index_document(document_id: str, source_path: Path) -> None:
    try:
        parsed = parse_document(source_path)
        chunks = split_pages(parsed, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            raise ValueError("文档中没有可索引的文本")
        embeddings = embedding_service.encode([str(item["content"]) for item in chunks])
        chunk_ids = [str(uuid.uuid4()) for _ in chunks]
        now = utc_now()
        with connect() as db:
            db.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            db.executemany(
                """
                INSERT INTO chunks
                (id, document_id, content, page_number, section_title,
                 chunk_index, embedding, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk_ids[index],
                        document_id,
                        item["content"],
                        item["page_number"],
                        item["section_title"],
                        index,
                        serialize_embedding(embeddings[index]),
                        now,
                    )
                    for index, item in enumerate(chunks)
                ],
            )
            db.execute(
                """
                UPDATE documents
                SET status = 'ready', page_count = ?, chunk_count = ?, error_message = NULL
                WHERE id = ?
                """,
                (parsed.page_count, len(chunks), document_id),
            )
        vector_store.upsert(
            ids=chunk_ids,
            documents=[str(item["content"]) for item in chunks],
            embeddings=embeddings,
            metadatas=[
                {
                    "document_id": document_id,
                    "page_number": int(item["page_number"] or 0),
                    "section_title": str(item["section_title"] or ""),
                }
                for item in chunks
            ],
        )
    except Exception as exc:
        with connect() as db:
            db.execute(
                "UPDATE documents SET status = 'failed', error_message = ? WHERE id = ?",
                (str(exc)[:500], document_id),
            )
        raise


def list_documents() -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute(
            """
            SELECT id, name, file_type, status, page_count, chunk_count,
                   error_message, created_at
            FROM documents ORDER BY created_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_document(document_id: str) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute(
            "SELECT * FROM documents WHERE id = ?", (document_id,)
        ).fetchone()
    return dict(row) if row else None


def delete_document(document_id: str) -> bool:
    document = get_document(document_id)
    if not document:
        return False
    vector_store.delete_document(document_id)
    with connect() as db:
        db.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    source = Path(document["source_path"])
    if source.exists() and settings.uploads_dir in source.parents:
        source.unlink()
    return True


def reindex_document(document_id: str) -> None:
    document = get_document(document_id)
    if not document:
        raise LookupError("文档不存在")
    vector_store.delete_document(document_id)
    with connect() as db:
        db.execute(
            "UPDATE documents SET status = 'processing', error_message = NULL WHERE id = ?",
            (document_id,),
        )
    index_document(document_id, Path(document["source_path"]))


def retrieve(question: str, top_k: int | None = None) -> dict[str, list[dict[str, Any]]]:
    question_embedding = embedding_service.encode([question])[0]
    candidates = vector_store.query(question_embedding, top_k or settings.retrieval_top_k)
    for index, item in enumerate(candidates, start=1):
        item["vector_rank"] = index
    ranked = reranker_service.rerank(question, [dict(item) for item in candidates])
    return {"candidates": candidates, "ranked": ranked}


def select_contexts(ranked: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not ranked:
        return []
    relevant = [
        item
        for item in ranked
        if float(item.get("rerank_score", 0.0)) >= settings.min_relevance
    ]
    return relevant[: settings.context_top_k]


def citations_from_contexts(contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "index": index,
            "chunk_id": item["id"],
            "document_id": item["document_id"],
            "file_name": item["file_name"],
            "page_number": item.get("page_number"),
            "section_title": item.get("section_title"),
            "content": item["content"],
            "vector_score": round(float(item.get("vector_score", 0.0)), 4),
            "rerank_score": round(float(item.get("rerank_score", 0.0)), 4),
        }
        for index, item in enumerate(contexts, start=1)
    ]


def copy_upload(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
