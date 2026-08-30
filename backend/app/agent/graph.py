from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent.state import AgentState
from app.agent.tools import TOOLS, parse_tool_result
from app.core.config import settings
from app.services.llm import SYSTEM_PROMPT


AGENT_PROMPT = SYSTEM_PROMPT + """

你可以使用以下工具完成任务：
- search_knowledge：查询制度、流程和技术资料，优先用于企业内部事实问题。
- get_source：根据片段 ID 获取完整原文，用于核实引用。
- list_documents：查看当前知识库中的文档。
- get_document_content：获取整份文档内容，用于摘要和文档级分析。

工具使用规则：
1. 对企业内部事实优先调用 search_knowledge，不要凭常识猜测。
2. 对摘要或文档对比问题，先使用 list_documents，再使用 get_document_content。
3. 如果已有结果足以回答，不要重复调用工具。
4. 最多连续调用 3 轮工具；资料不足时直接说明。
5. 最终答案必须简洁，并引用真实来源；没有依据时必须拒答。
"""


def build_graph(model: Any | None = None):
    graph = StateGraph(AgentState)

    async def agent_node(state: AgentState) -> dict[str, list[BaseMessage]]:
        if model is None:
            return _demo_agent_node(state)
        messages = [SystemMessage(content=AGENT_PROMPT), *state.get("messages", [])]
        response = await model.ainvoke(messages)
        return {"messages": [response]}

    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


def _demo_agent_node(state: AgentState) -> dict[str, list[BaseMessage]]:
    tool_messages = [message for message in state.get("messages", []) if isinstance(message, ToolMessage)]
    if not tool_messages:
        return {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "search_knowledge",
                            "args": {"question": state["question"], "top_k": settings.retrieval_top_k},
                            "id": "demo-search-1",
                            "type": "tool_call",
                        }
                    ],
                )
            ]
        }
    result = parse_tool_result(tool_messages[-1].content)
    contexts = result.get("results", [])
    if not contexts:
        answer = "当前知识库未检索到足够依据，无法确认。"
    else:
        excerpts = []
        for index, item in enumerate(contexts[:3], start=1):
            content = item["content"].replace("\n", " ").strip()
            excerpts.append(f"{content[:180]}{'……' if len(content) > 180 else ''} [{index}]")
        answer = "根据当前知识库，相关资料如下：\n\n" + "\n\n".join(excerpts)
    return {"messages": [AIMessage(content=answer)]}

