from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from app.agent.graph import build_graph
from app.agent.tools import TOOLS, parse_tool_result
from app.core.config import settings


@dataclass
class AgentResult:
    answer: str
    citations: list[dict[str, Any]]
    tool_trace: list[dict[str, Any]]


class AgentService:
    def __init__(self) -> None:
        self.model = self._create_model()
        self.graph = build_graph(self.model)
        self.mode = "langgraph-api" if self.model is not None else "langgraph-demo"

    def _create_model(self):
        if not settings.llm_api_key:
            return None
        try:
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                model=settings.llm_model,
                temperature=0.1,
                timeout=60,
                max_retries=2,
            ).bind_tools(TOOLS)
        except Exception:
            return None

    async def run(
        self, question: str, history: list[dict[str, str]] | None = None
    ) -> AgentResult:
        messages: list[BaseMessage] = []
        for item in history or []:
            if item["role"] == "user":
                messages.append(HumanMessage(content=item["content"]))
            elif item["role"] == "assistant":
                messages.append(AIMessage(content=item["content"]))
        messages.append(HumanMessage(content=question))
        final_state = await self.graph.ainvoke(
            {"question": question, "messages": messages, "citations": [], "tool_trace": []},
            config={"recursion_limit": 12},
        )
        answer = _last_ai_content(final_state.get("messages", []))
        citations, tool_trace = _extract_tool_outputs(final_state.get("messages", []))
        return AgentResult(
            answer=answer,
            citations=citations,
            tool_trace=tool_trace,
        )


def _last_ai_content(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage) and message.content:
            return str(message.content)
    return "当前知识库未检索到足够依据，无法确认。"


def _extract_tool_outputs(messages: list[BaseMessage]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    citations: list[dict[str, Any]] = []
    trace: list[dict[str, Any]] = []
    seen: set[str] = set()
    for message in messages:
        if isinstance(message, AIMessage) and message.tool_calls:
            for call in message.tool_calls:
                trace.append({"type": "tool_call", "name": call.get("name"), "args": call.get("args", {})})
        if isinstance(message, ToolMessage):
            parsed = parse_tool_result(message.content)
            trace.append({"type": "tool_result", "name": message.name, "result_type": parsed.get("type")})
            for citation in parsed.get("results", []):
                key = citation.get("chunk_id")
                if key and key not in seen:
                    seen.add(key)
                    citations.append(citation)
            source = parsed.get("source") if parsed.get("type") == "source" else None
            if parsed.get("found") and source and source.get("id") not in seen:
                seen.add(source["id"])
                citations.append({
                    "chunk_id": source["id"],
                    "document_id": source["document_id"],
                    "file_name": source["file_name"],
                    "page_number": source.get("page_number"),
                    "section_title": source.get("section_title"),
                    "content": source["content"],
                    "vector_score": 0.0,
                    "rerank_score": 0.0,
                })
    for index, citation in enumerate(citations, start=1):
        citation["index"] = index
    return citations, trace


agent_service = AgentService()
