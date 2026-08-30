from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

from app.core.database import connect
from app.services.rag import citations_from_contexts, retrieve, select_contexts


@tool
def search_knowledge(question: str, top_k: int = 20) -> str:
    """搜索企业知识库，返回带来源和相关性分数的候选内容。"""
    result = retrieve(question, top_k=max(1, min(top_k, 50)))
    contexts = select_contexts(result["ranked"])
    return json.dumps(
        {
            "type": "knowledge_search",
            "question": question,
            "results": citations_from_contexts(contexts),
            "candidate_count": len(result["candidates"]),
        },
        ensure_ascii=False,
    )


@tool
def get_source(chunk_id: str) -> str:
    """根据知识片段 ID 获取完整原文和来源信息。"""
    with connect() as db:
        row = db.execute(
            """
            SELECT c.id, c.document_id, c.content, c.page_number,
                   c.section_title, d.name AS file_name
            FROM chunks c JOIN documents d ON d.id = c.document_id
            WHERE c.id = ? AND d.status = 'ready'
            """,
            (chunk_id,),
        ).fetchone()
    if not row:
        return json.dumps({"type": "source", "found": False}, ensure_ascii=False)
    return json.dumps(
        {"type": "source", "found": True, "source": dict(row)},
        ensure_ascii=False,
    )


@tool
def list_documents() -> str:
    """列出当前已完成索引的企业文档。"""
    with connect() as db:
        rows = db.execute(
            """
            SELECT id, name, file_type, page_count, chunk_count, created_at
            FROM documents WHERE status = 'ready' ORDER BY created_at DESC
            """
        ).fetchall()
    return json.dumps(
        {"type": "document_list", "documents": [dict(row) for row in rows]},
        ensure_ascii=False,
    )


@tool
def get_document_content(document_id: str) -> str:
    """获取指定文档的已索引内容，适合摘要或文档级分析。"""
    with connect() as db:
        rows = db.execute(
            """
            SELECT id, content, page_number, section_title, chunk_index
            FROM chunks WHERE document_id = ? ORDER BY chunk_index
            """,
            (document_id,),
        ).fetchall()
        document = db.execute(
            "SELECT id, name, page_count, chunk_count FROM documents WHERE id = ? AND status = 'ready'",
            (document_id,),
        ).fetchone()
    if not document:
        return json.dumps({"type": "document_content", "found": False}, ensure_ascii=False)
    return json.dumps(
        {
            "type": "document_content",
            "found": True,
            "document": dict(document),
            "chunks": [dict(row) for row in rows],
        },
        ensure_ascii=False,
    )


TOOLS = [search_knowledge, get_source, list_documents, get_document_content]
TOOL_MAP = {item.name: item for item in TOOLS}


def parse_tool_result(content: Any) -> dict[str, Any]:
    if isinstance(content, list):
        content = "".join(str(item) for item in content)
    try:
        parsed = json.loads(str(content))
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}

