from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import settings


SYSTEM_PROMPT = """你是企业内部知识库问答助手。请严格遵守：
1. 只能依据提供的知识库上下文回答，不得补充上下文之外的事实。
2. 每个关键结论后使用 [1]、[2] 形式标记对应引用。
3. 如果资料不足，回答“当前知识库未检索到足够依据，无法确认。”
4. 不得伪造文件名、页码、条款或引用。
5. 先给结论，再说明条件、步骤或例外，语言简洁明确。"""


class LLMService:
    @property
    def mode(self) -> str:
        return "api" if settings.llm_api_key else "extractive-demo"

    async def stream_answer(
        self, question: str, contexts: list[dict[str, Any]]
    ) -> AsyncIterator[str]:
        if not settings.llm_api_key:
            answer = self._fallback_answer(question, contexts)
            for index in range(0, len(answer), 16):
                yield answer[index : index + 16]
            return

        context_text = "\n\n".join(
            f"[{index}] 文件：{item['file_name']}；页码：{item.get('page_number') or '无'}\n{item['content']}"
            for index, item in enumerate(contexts, start=1)
        )
        payload = {
            "model": settings.llm_model,
            "stream": True,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"知识库上下文：\n{context_text}\n\n用户问题：{question}",
                },
            ],
        }
        headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
        url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    raw = line[6:]
                    if raw == "[DONE]":
                        break
                    data = json.loads(raw)
                    delta = data.get("choices", [{}])[0].get("delta", {}).get("content")
                    if delta:
                        yield delta

    def _fallback_answer(self, question: str, contexts: list[dict[str, Any]]) -> str:
        if not contexts:
            return "当前知识库未检索到足够依据，无法确认。"
        excerpts = []
        for index, item in enumerate(contexts[:3], start=1):
            content = item["content"].replace("\n", " ").strip()
            if len(content) > 180:
                content = content[:180].rstrip() + "……"
            excerpts.append(f"{content} [{index}]")
        return "根据当前知识库，相关资料如下：\n\n" + "\n\n".join(excerpts)


llm_service = LLMService()

