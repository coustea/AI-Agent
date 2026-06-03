# -*- coding: utf-8 -*-
"""TutorAgent：基于上下文初始化的智能辅导编排器。

负责 LangGraph 图编排、路由条件控制、节点分发以及前端 SSE 事件的流式分发。
具体的问答和绘图逻辑已分别抽取至 answer.py 和 diagram.py。
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.chat.request import ChatHistoryMessage
from app.chat.schemas import TeachingDiagram, TutorAgentContext, TutorState
from app.infra.context import runtime_context as chat_runtime_context
from app.chat.runtime import prepare_tutor_state
from app.chat.utils import (
    classify_route,
    extract_question,
    is_unusable_reply_text,
    node_timer,
    normalize_message_content,
    stream_event,
    truncate,
)
from app.config import LANGGRAPH_DEBUG
from app.infra.llm import get_llm
from app.infra.logging import get_logger

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# LangGraph 递归限制
GRAPH_RECURSION_LIMIT = 30

# 图节点名称集合
GRAPH_NODE_NAMES = {
    "classify",
    "answer_node",
    "search_node",
    "attachment_answer",
    "teaching_diagram_generate",
}

# 回答节点名称集合（会发送 token 事件，包含逻辑节点和内部标识）
ANSWER_NODE_NAMES = {"answer_node", "direct_answer", "spark_summary", "attachment_answer"}


def _graph_stream_kwargs() -> dict[str, Any]:
    """构建 LangGraph 流式参数。"""
    kwargs: dict[str, Any] = {
        "version": "v2",
        "config": {"recursion_limit": GRAPH_RECURSION_LIMIT},
    }
    if LANGGRAPH_DEBUG:
        kwargs["debug"] = True
    return kwargs


class TutorAgent:
    """智能辅导 Agent — 状态图与 SSE 编排层。

    四大对话路径：
    1. classify -> answer_node -> diagram(可选)
    2. classify -> search_node -> answer_node -> diagram(可选)
    3. classify -> attachment_answer -> diagram(可选)
    4. classify -> teaching_diagram_generate (纯图解生成模式)
    """

    def __init__(self, context: TutorAgentContext) -> None:
        """初始化 TutorAgent。"""
        self.context = context
        self.llm = get_llm()
        self.graph = None
        self._init_lock = asyncio.Lock()

        logger.info("[TutorAgent] 初始化完成")

    # ------------------------------------------------------------------
    # 兼容与辅助包装方法
    # ------------------------------------------------------------------

    async def _stream_answer_with_retry(
        self,
        messages: list[Any],
        *,
        node_name: str,
        config: RunnableConfig,
        runnable: Any = None,
        fallback_text: str = "抱歉，我暂时无法回答这个问题，请稍后重试。",
        retry_prompt: str = "请重新回答用户问题，给出完整、可读、适合教学场景的中文回答。",
    ) -> AIMessage:
        """流式回答辅助方法（委托至 answer.py）。"""
        from app.chat.answer import stream_answer_with_retry
        return await stream_answer_with_retry(
            agent=self,
            messages=messages,
            node_name=node_name,
            config=config,
            runnable=runnable,
            fallback_text=fallback_text,
            retry_prompt=retry_prompt,
        )

    @staticmethod
    def _scoped_answer_prompt(
        system_prompt: str,
        *,
        question: str,
        diagram_enabled: bool,
    ) -> str:
        """回答提示词组装辅助方法（委托至 answer.py）。"""
        from app.chat.answer import _scoped_answer_prompt
        return _scoped_answer_prompt(
            system_prompt,
            question=question,
            diagram_enabled=diagram_enabled,
        )

    async def _generate_teaching_diagram(
        self,
        *,
        question: str,
        answer: str,
        state: TutorState,
    ) -> TeachingDiagram:
        """图板生成辅助方法（委托至 diagram.py）。"""
        from app.chat.diagram import generate_teaching_diagram
        return await generate_teaching_diagram(
            agent=self,
            question=question,
            answer=answer,
            state=state,
        )

    # ------------------------------------------------------------------
    # 图构建
    # ------------------------------------------------------------------

    async def _ensure_graph(self) -> None:
        """构建 LangGraph 状态图。"""
        if self.graph is not None:
            return

        # 使用异步锁保证 LangGraph 状态图只被编译和初始化一次
        async with self._init_lock:
            if self.graph is not None:
                return

            graph = StateGraph(TutorState)
            
            # 添加节点
            graph.add_node("classify", self._classify_node)
            graph.add_node("answer_node", self._answer_node)
            graph.add_node("search_node", self._search_node)
            graph.add_node("attachment_answer", self._attachment_answer_node)
            graph.add_node("teaching_diagram_generate", self._teaching_diagram_generate_node)

            # 添加边
            graph.add_edge(START, "classify")
            graph.add_conditional_edges(
                "classify",
                classify_route,
                {
                    "direct": "answer_node",
                    "diagram_only": "teaching_diagram_generate",
                    "search": "search_node",
                    "attachment_needed": "attachment_answer",
                },
            )
            graph.add_conditional_edges(
                "answer_node",
                self._route_after_answer,
                {
                    "diagram": "teaching_diagram_generate",
                    "end": END,
                },
            )
            graph.add_edge("search_node", "answer_node")
            graph.add_conditional_edges(
                "attachment_answer",
                self._route_after_answer,
                {
                    "diagram": "teaching_diagram_generate",
                    "end": END,
                },
            )
            graph.add_edge("teaching_diagram_generate", END)

            self.graph = graph.compile()

    # ------------------------------------------------------------------
    # 条件路由
    # ------------------------------------------------------------------

    @staticmethod
    def _route_after_answer(state: dict) -> str:
        """在文字回答完成后运行可选的图解生成。"""
        return "diagram" if state.get("need_teaching_diagram", False) else "end"

    # ------------------------------------------------------------------
    # 节点实现 (状态机节点包装)
    # ------------------------------------------------------------------

    async def _classify_node(self, state: TutorState) -> dict[str, Any]:
        """分类节点：决定意图路由与执行模式。

        知识库检索已改为 Agent Tool，不再作为独立节点。
        当 enable_knowledge_base=True 时，会在 state 中标记，供 answer_node 绑定工具时使用。
        """
        from app.chat.diagram import explicit_diagram_requested, diagram_only_requested, previous_teaching_exchange

        user_id = state.get("user_id")
        session_id = state.get("session_id")
        messages = state.get("messages") or []
        attachments = state.get("attachments") or []
        enable_web_search = bool(state.get("enable_web_search", False))
        enable_knowledge_base = bool(state.get("enable_knowledge_base", False))
        need_teaching_diagram = bool(state.get("need_teaching_diagram", False))
        user_message = extract_question(messages)

        has_attachments = bool(attachments)

        with node_timer("classify", user=user_id, session=session_id):
            # 判断是否需要请求画图
            need_diagram = need_teaching_diagram or explicit_diagram_requested(user_message)

            state_updates: dict[str, Any] = {}
            if need_diagram != need_teaching_diagram:
                state_updates["need_teaching_diagram"] = need_diagram

            # 根据附件情况、搜索开关以及是否只要画图，决定路由去向
            # 知识库检索改为 Tool 方式，不作为独立路由
            if has_attachments:
                if enable_web_search:
                    execution_mode = "attachment_search"
                else:
                    execution_mode = "attachment"
                route = "attachment_needed"
            elif enable_web_search:
                route = "search"
                execution_mode = "search"
            elif enable_knowledge_base:
                # 知识库开启但没有联网搜索时，走 direct 路由，由 answer_node 绑定知识库工具
                route = "direct"
                execution_mode = "knowledge_tool"
            elif need_diagram and diagram_only_requested(user_message):
                _, prior_answer = previous_teaching_exchange(list(messages))
                if prior_answer:
                    route = "diagram_only"
                    execution_mode = "diagram_only"
                else:
                    need_diagram = False
                    route = "direct"
                    execution_mode = "direct"
                    state_updates["need_teaching_diagram"] = False
            else:
                route = "direct"
                execution_mode = "direct"

            logger.debug(
                "[TutorAgent] 路由分类 route=%s execution_mode=%s need_diagram=%s web_search=%s knowledge=%s question=%s",
                route,
                execution_mode,
                need_diagram,
                enable_web_search,
                enable_knowledge_base,
                truncate(user_message, 120),
            )

            state_updates.update({
                "route": route,
                "execution_mode": execution_mode,
            })

            return state_updates

    async def _answer_node(self, state: TutorState, config: RunnableConfig) -> dict[str, Any]:
        """统一回答节点 (合并直接回答与检索总结)。"""
        from app.chat.answer import answer_node
        return await answer_node(self, state, config)

    async def _search_node(self, state: TutorState) -> dict[str, Any]:
        """搜索节点：委托 collect_search_context 获取参考资料。"""
        from app.chat.answer import collect_search_context

        messages = state.get("messages") or []
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        system_prompt = state.get("system_prompt", "")
        question = extract_question(messages)
        attachment_context = str(state.get("attachment_analysis_context", "")).strip()

        with node_timer("search_node", user=user_id, session=session_id):
            logger.info("[TutorAgent] 联网搜索节点 question=%s", truncate(question, 180))

            search_result, knowledge_sources = await collect_search_context(
                agent=self,
                question=question,
                system_prompt=system_prompt,
                messages=messages,
                attachment_context=attachment_context,
                include_knowledge=bool(state.get("enable_knowledge_base", False)),
            )

            logger.debug("[TutorAgent] search_node 完成 preview=%s", truncate(search_result, 220))

            return {
                "search_result": search_result,
                "knowledge_sources": knowledge_sources,
                "termination_reason": "search_done",
            }

    async def _attachment_answer_node(self, state: TutorState, config: RunnableConfig) -> dict[str, Any]:
        """附件回答节点。"""
        from app.chat.answer import attachment_answer_node
        return await attachment_answer_node(self, state, config)

    async def _teaching_diagram_generate_node(self, state: TutorState) -> TutorState:
        """教学图解生成节点。"""
        from app.chat.diagram import teaching_diagram_generate_node
        return await teaching_diagram_generate_node(self, state)

    # ------------------------------------------------------------------
    # 主入口：SSE 流式对话
    # ------------------------------------------------------------------

    async def chat_stream(
        self,
        history: list[ChatHistoryMessage],
    ):
        """流式生成对话响应。"""
        context = self.context
        current_message = ""
        for item in reversed(history):
            if item.role == "user" and item.content.strip():
                current_message = item.content.strip()
                break

        logger.info(
            "[TutorAgent] 对话开始 message=%s attachments=%s web_search=%s knowledge=%s",
            truncate(current_message, 180),
            len(context.attachments),
            context.enable_web_search,
            context.enable_knowledge_base,
        )

        await self._ensure_graph()

        # 将前端传入的历史消息与 Agent 初始化 Context 合并，生成 LangGraph 初始状态
        initial_state = prepare_tutor_state(context, history)
        initial_msg_count = len(initial_state.get("messages", []))

        full_reply = ""
        runtime_state: dict[str, Any] = dict(initial_state)
        graph_error_text = ""
        active_node = ""
        started_at = time.monotonic()
        first_token_ms: int | None = None

        try:
            with chat_runtime_context(context.user_id, context.session_id):
                # 监听 LangGraph 运行过程中发出的各类事件，并转换为 SSE 数据流给前端
                async for event in self.graph.astream_events(initial_state, **_graph_stream_kwargs()):
                    kind = event.get("event", "")
                    name = event.get("name", "")

                    # 节点开始事件：给前端发送状态更新信息，展示“正在思考...”等提示语
                    if kind == "on_chain_start" and name in GRAPH_NODE_NAMES:
                        active_node = name
                        if name == "classify":
                            yield stream_event(
                                "status",
                                {"stage": name, "message": "正在判断最合适的答疑方式..."},
                            )
                        elif name == "search_node":
                            yield stream_event(
                                "status",
                                {"stage": name, "message": "正在联网搜索与问题相关的资料..."},
                            )
                        elif name == "knowledge_node":
                            yield stream_event(
                                "status",
                                {"stage": name, "message": "正在检索本地知识库..."},
                            )
                        elif name == "answer_node":
                            # 自适应子节点状态消息
                            is_search = bool(runtime_state.get("search_result"))
                            stage_name = "spark_summary" if is_search else "direct_answer"
                            message = "正在结合检索资料组织回答..." if is_search else "正在组织回答..."
                            yield stream_event(
                                "status",
                                {"stage": stage_name, "message": message},
                            )
                        elif name == "attachment_answer":
                            yield stream_event(
                                "status",
                                {"stage": name, "message": "正在结合附件内容组织回答..."},
                            )
                        elif name == "teaching_diagram_generate":
                            yield stream_event(
                                "status",
                                {
                                    "stage": name,
                                    "message": "正在生成图解说明...",
                                },
                            )

                    # 节点结束事件
                    if kind == "on_chain_end" and name in GRAPH_NODE_NAMES:
                        active_node = ""
                        node_output = event.get("data", {}).get("output", {})
                        if isinstance(node_output, dict):
                            for key, value in node_output.items():
                                if key == "messages" and isinstance(value, list):
                                    runtime_state[key] = list(runtime_state.get(key, [])) + value
                                else:
                                    runtime_state[key] = value

                    # 自定义 answer_token 事件处理：接收大模型流式生成的每一个 Token，透传给前端做到打字机效果
                    if kind == "on_custom_event" and name == "answer_token":
                        payload = event.get("data", {})
                        node_name = payload.get("node") if isinstance(payload, dict) else active_node
                        chunk_text = payload.get("text", "") if isinstance(payload, dict) else ""
                        if node_name in ANSWER_NODE_NAMES and chunk_text:
                            if first_token_ms is None:
                                first_token_ms = int((time.monotonic() - started_at) * 1000)
                                logger.info("[TutorAgent] 首个 token 已发送 first_token_ms=%s", first_token_ms)
                            full_reply += chunk_text
                            yield stream_event("token", chunk_text)

                    if kind == "on_custom_event" and name == "learner_context_status":
                        payload = event.get("data", {})
                        if isinstance(payload, dict):
                            yield stream_event("status", payload)

                    # 兼容未产生流式 chunk 的兜底逻辑
                    if kind == "on_chain_end" and name in ANSWER_NODE_NAMES and not full_reply:
                        node_output = event.get("data", {}).get("output", {})
                        if isinstance(node_output, dict):
                            final_messages = node_output.get("messages")
                            if isinstance(final_messages, list):
                                final_ai = next(
                                    (msg for msg in reversed(final_messages) if isinstance(msg, AIMessage)),
                                    None,
                                )
                                final_text = normalize_message_content(final_ai.content if final_ai else "")
                                if final_text:
                                    if first_token_ms is None:
                                        first_token_ms = int((time.monotonic() - started_at) * 1000)
                                        logger.info("[TutorAgent] 首个 token 已发送 first_token_ms=%s", first_token_ms)
                                    full_reply = final_text
                                    yield stream_event("token", final_text)

        except Exception as exc:
            logger.exception("[TutorAgent] 请求异常")
            graph_error_text = f"服务器出错: {exc}"

        logger.info(
            "[TutorAgent] 请求结束 termination_reason=%s first_token_ms=%s total_ms=%s",
            runtime_state.get("termination_reason", ""),
            first_token_ms,
            int((time.monotonic() - started_at) * 1000),
        )

        if graph_error_text:
            yield stream_event("error", graph_error_text)
            yield stream_event("done", {"session_id": context.session_id, "error": True})
            return

        if not full_reply and runtime_state.get("execution_mode") != "diagram_only":
            messages = runtime_state.get("messages", [])
            if isinstance(messages, list):
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage):
                        full_reply = normalize_message_content(msg.content)
                        break

        teaching_diagram = runtime_state.get("teaching_diagram")
        knowledge_sources = runtime_state.get("knowledge_sources")

        # 从大模型生成的所有新消息中提取并聚合本轮产生的 Tool Calls 和 Token 消耗数据
        tool_calls = []
        usage_metadata = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        has_usage = False
        messages_list = runtime_state.get("messages", [])
        if isinstance(messages_list, list) and len(messages_list) > initial_msg_count:
            for msg in messages_list[initial_msg_count:]:
                if isinstance(msg, AIMessage):
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        tool_calls.extend(msg.tool_calls)
                    if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                        has_usage = True
                        usage_metadata["input_tokens"] += msg.usage_metadata.get("input_tokens", 0)
                        usage_metadata["output_tokens"] += msg.usage_metadata.get("output_tokens", 0)
                        usage_metadata["total_tokens"] += msg.usage_metadata.get("total_tokens", 0)
        
        final_usage_metadata = usage_metadata if has_usage else None

        # 打印关键单行日志，方便观察本轮会话的工具调用和 Token 消耗情况
        logger.info(
            "[TutorAgent] 会话 %s 回答生成完毕 | 提取到 ToolCalls: %d 个 | Token使用量: %s",
            context.session_id,
            len(tool_calls),
            final_usage_metadata,
        )

        if not isinstance(teaching_diagram, dict) and is_unusable_reply_text(full_reply) and not tool_calls:
            yield stream_event("error", "模型未返回有效内容，请重试。")
            yield stream_event("done", {"session_id": context.session_id, "error": True})
            return

        if isinstance(teaching_diagram, dict):
            yield stream_event("diagram", teaching_diagram)

        # 最后一并发出 done 事件，将完整的响应和工具消耗元数据传给 service 层落库
        yield stream_event(
            "done",
            {
                "session_id": context.session_id,
                "full_response": full_reply,
                "knowledge_sources": knowledge_sources or [],
                "resource_mode": "none",
                "resource": None,
                "teaching_diagram": teaching_diagram,
                "resources": {"teaching_diagram": teaching_diagram, "video": None},
                "tool_calls": tool_calls,
                "usage_metadata": final_usage_metadata,
            },
        )
