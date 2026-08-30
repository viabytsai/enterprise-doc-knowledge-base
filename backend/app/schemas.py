from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None


class DebugRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=20, ge=1, le=50)


class Citation(BaseModel):
    index: int
    chunk_id: str
    document_id: str
    file_name: str
    page_number: int | None
    section_title: str | None
    content: str
    vector_score: float
    rerank_score: float

