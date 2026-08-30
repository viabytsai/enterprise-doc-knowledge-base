from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from fastapi.responses import StreamingResponse

from app.agent.service import agent_service
from app.core.config import settings
from app.core.database import connect, utc_now
from app.schemas import ChatRequest, DebugRequest
from app.services.embeddings import embedding_service
from app.services.llm import llm_service
from app.services.parser import SUPPORTED_EXTENSIONS
from app.services.rag import (
    citations_from_contexts,
    create_document_record,
    delete_document,
    get_document,
    index_document,
    list_documents,
    reindex_document,
    retrieve,
    select_contexts,
)
from app.services.reranker import reranker_service
from app.services.vector_store import vector_store


router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "services": {
            "embedding": {"mode": embedding_service.mode, "detail": embedding_service.detail},
            "reranker": {"mode": reranker_service.mode, "detail": reranker_service.detail},
            "vector_store": {"mode": vector_store.mode},
            "llm": {"mode": llm_service.mode, "model": settings.llm_model},
            "agent": {"mode": agent_service.mode, "framework": "LangGraph"},
        },
    }


@router.get("/stats")
def stats() -> dict[str, int]:
    with connect() as db:
        documents = db.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        ready = db.execute("SELECT COUNT(*) FROM documents WHERE status = 'ready'").fetchone()[0]
        chunks = db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    return {"documents": documents, "ready_documents": ready, "chunks": chunks}


@router.get("/documents")
def documents() -> list[dict[str, object]]:
    return list_documents()


@router.post("/documents", status_code=201)
async def upload_document(file: UploadFile = File(...)) -> dict[str, object]:
    original_name = Path(file.filename or "document").name
    suffix = Path(original_name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="仅支持 PDF、DOCX、Markdown 和 TXT")
    content = await file.read(settings.max_file_mb * 1024 * 1024 + 1)
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")
    if len(content) > settings.max_file_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"文件不能超过 {settings.max_file_mb} MB")

    storage_name = f"{uuid.uuid4()}{suffix}"
    destination = settings.uploads_dir / storage_name
    destination.write_bytes(content)
    document_id = create_document_record(original_name, suffix.lstrip("."), destination)
    try:
        index_document(document_id, destination)
    except Exception:
        document = get_document(document_id)
        raise HTTPException(status_code=422, detail=document["error_message"] if document else "解析失败")
    return get_document(document_id) or {}


@router.delete("/documents/{document_id}", status_code=204, response_class=Response)
def remove_document(document_id: str) -> Response:
    if not delete_document(document_id):
        raise HTTPException(status_code=404, detail="文档不存在")
    return Response(status_code=204)


@router.post("/documents/{document_id}/reindex")
def rebuild_document(document_id: str) -> dict[str, object]:
    try:
        reindex_document(document_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return get_document(document_id) or {}


@router.post("/retrieval/debug")
def debug_retrieval(request: DebugRequest) -> dict[str, object]:
    started = time.perf_counter()
    result = retrieve(request.question, request.top_k)
    contexts = select_contexts(result["ranked"])
    return {
        "question": request.question,
        "candidates": [_public_result(item) for item in result["candidates"]],
        "ranked": [_public_result(item) for item in result["ranked"]],
        "selected_chunk_ids": [item["id"] for item in contexts],
        "latency_ms": round((time.perf_counter() - started) * 1000),
    }


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    async def events():
        started = time.perf_counter()
        conversation_id = request.conversation_id or str(uuid.uuid4())
        if not request.conversation_id:
            with connect() as db:
                db.execute(
                    "INSERT INTO conversations (id, title, created_at) VALUES (?, ?, ?)",
                    (conversation_id, request.question[:40], utc_now()),
                )
        try:
            history = _conversation_history(conversation_id)
            result = await agent_service.run(request.question, history)
        except Exception as exc:
            yield _sse("error", {"message": f"Agent 执行失败：{str(exc)[:200]}"})
            return
        citations = result.citations
        yield _sse(
            "meta",
            {
                "conversation_id": conversation_id,
                "citations": citations,
                "tool_trace": result.tool_trace,
                "agent_mode": agent_service.mode,
            },
        )
        answer = result.answer
        for index in range(0, len(answer), 16):
            yield _sse("token", {"content": answer[index : index + 16]})
        latency_ms = round((time.perf_counter() - started) * 1000)
        with connect() as db:
            db.execute(
                """
                INSERT INTO messages
                (id, conversation_id, role, content, citations, latency_ms, created_at)
                VALUES (?, ?, 'user', ?, '[]', NULL, ?)
                """,
                (str(uuid.uuid4()), conversation_id, request.question, utc_now()),
            )
            db.execute(
                """
                INSERT INTO messages
                (id, conversation_id, role, content, citations, latency_ms, created_at)
                VALUES (?, ?, 'assistant', ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    conversation_id,
                    answer,
                    json.dumps(citations, ensure_ascii=False),
                    latency_ms,
                    utc_now(),
                ),
            )
        yield _sse("done", {"latency_ms": latency_ms})

    return StreamingResponse(events(), media_type="text/event-stream")


def _sse(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _conversation_history(conversation_id: str) -> list[dict[str, str]]:
    with connect() as db:
        rows = db.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY created_at",
            (conversation_id,),
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def _public_result(item: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in item.items()
        if key not in {"embedding", "created_at"}
    }
