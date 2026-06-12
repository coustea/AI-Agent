"""推理 Agent — 接收完整消息列表，决定「调工具还是直接回答」。

调用链路：service.chat() → agent.reason(messages, ...) → LangChain tool call 或 LLM 回答
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, AnyMessage

from app.chat.schemas import ConstraintReport, FinalAnswer, FinalAnswerStream, ToolIntent
from app.chat.utils import normalize_message_content
from app.infra.llm import get_llm

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


class ReasoningAgent:
    """LangChain tool-calling tutor agent — 纯推理器。

    接收完整的消息列表（由 service.build_messages() 构建），
    让模型决定是否调用工具，并将工具调用转换为 ToolIntent。
    实际工具执行由 service.chat() 负责。
    """

    def __init__(self, llm: Any | None = None, tools: list[Any] | None = None) -> None:
        """初始化推理代理
        - llm: 大语言模型实例，默认使用配置的模型
        - tools: 可用工具列表，模型从中选择要调用的工具
        """
        self.llm = llm or get_llm()
        self.tools = list(tools or [])

    async def reason(
        self,
        messages: list[AnyMessage],
        constraints: ConstraintReport,
        tools: list[Any] | None = None,
    ) -> ToolIntent | FinalAnswer | FinalAnswerStream:
        """核心推理方法：接收完整消息列表，让模型决定是调用工具还是直接回答
        - 如果模型选择工具 → 返回 ToolIntent，由 chat() 执行
        - 如果模型直接回答 → 返回 FinalAnswer 或 FinalAnswerStream
        """

        # ── 调用 LLM ──
        available_tools = list(self.tools if tools is None else tools)
        model = self.llm.model.bind_tools(available_tools) if available_tools else None

        if not hasattr(self.llm, "astream"):
            response = await self.llm.ainvoke(messages, model=model, temperature=0.25)
            return await self._outcome_from_response(response, constraints, messages)

        stream = self.llm.astream(messages, model=model, temperature=0.25)
        try:
            first_chunk = await stream.__anext__()
        except StopAsyncIteration:
            return FinalAnswer(answer="")

        tool_calls = getattr(first_chunk, "tool_calls", None)
        if isinstance(tool_calls, list) and tool_calls:
            # 如果第一个 chunk 包含工具调用，累积所有 chunk 以获取完整工具调用
            accumulated = first_chunk
            async for chunk in stream:
                accumulated += chunk

            # 从累积的响应中提取第一个未执行过的工具调用
            tool_call = self._first_new_tool_call(accumulated, constraints)
            if tool_call is not None:
                return ToolIntent(
                    tool_name=str(tool_call.get("name") or ""),
                    payload=self._tool_payload(tool_call),
                )

            # 如果没有新的工具调用，提取回答内容
            answer = normalize_message_content(getattr(accumulated, "content", ""))
            # 如果回答为空，重试一次（不绑定工具）
            if not answer:
                response = await self.llm.ainvoke(messages, model=None, temperature=0.25)
                answer = normalize_message_content(getattr(response, "content", ""))
            return FinalAnswer(answer=answer)
        else:
            # 流式文本生成：逐块 yield 内容给前端
            async def text_generator():
                content = getattr(first_chunk, "content", "")
                if isinstance(content, list) and content:
                    content = content[0].get("text", "")
                content_str = normalize_message_content(content)
                if content_str:
                    yield content_str

                async for chunk in stream:
                    chunk_content = getattr(chunk, "content", "")
                    if isinstance(chunk_content, list) and chunk_content:
                        chunk_content = chunk_content[0].get("text", "")
                    chunk_str = normalize_message_content(chunk_content)
                    if chunk_str:
                        yield chunk_str

            return FinalAnswerStream(text_generator())

    async def _outcome_from_response(
        self,
        response: Any,
        constraints: ConstraintReport,
        messages: list[Any],
    ) -> ToolIntent | FinalAnswer:
        """处理非流式 LLM 响应，提取工具调用或最终回答"""
        tool_calls = getattr(response, "tool_calls", None)
        if isinstance(tool_calls, list) and tool_calls:
            # 提取第一个未执行过的工具调用
            tool_call = self._first_new_tool_call(response, constraints)
            if tool_call is not None:
                return ToolIntent(
                    tool_name=str(tool_call.get("name") or ""),
                    payload=self._tool_payload(tool_call),
                )
            # 如果没有新的工具调用，提取回答内容
            answer = normalize_message_content(getattr(response, "content", ""))
            # 如果回答为空，重试一次（不绑定工具）
            if not answer:
                retry_response = await self.llm.ainvoke(messages, model=None, temperature=0.25)
                answer = normalize_message_content(getattr(retry_response, "content", ""))
            return FinalAnswer(answer=answer)
        # 没有工具调用，直接返回回答
        answer = normalize_message_content(getattr(response, "content", ""))
        return FinalAnswer(answer=answer)

    def _first_new_tool_call(self, response: Any, constraints: ConstraintReport) -> dict[str, Any] | None:
        """从模型响应中提取第一个未执行过的工具调用
        避免重复调用已执行的工具，将重复的工具记录到 skipped_tools
        """
        tool_calls = getattr(response, "tool_calls", None)
        if not isinstance(tool_calls, list):
            return None
        executed = set(constraints.executed_tools)
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue
            name = str(tool_call.get("name") or "").strip()
            # 如果工具未执行过，返回该工具调用
            if name and name not in executed:
                return tool_call
            # 如果工具已执行过，记录到跳过列表
            if name:
                constraints.skipped_tools.append(name)
        return None

    def _tool_payload(self, tool_call: dict[str, Any]) -> dict[str, Any]:
        """提取工具调用的参数，处理多种格式（dict/str/JSON字符串）"""
        args = tool_call.get("args")
        # 如果 args 已经是字典，直接返回
        if isinstance(args, dict):
            return args
        # 如果 args 是 JSON 字符串，解析为字典
        if isinstance(args, str):
            try:
                parsed = json.loads(args)
            except json.JSONDecodeError:
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return {}
