from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    question: str
    messages: Annotated[list[BaseMessage], add_messages]
    citations: list[dict[str, Any]]
    tool_trace: list[dict[str, Any]]

