# -*- coding: utf-8 -*-
"""TutorAgent: 轻量级教育场景编排器。

当前工作流：
    START -> classify
      ├─ direct → direct_answer → END（无图谱）
      ├─ direct+graph → direct_answer → knowledge_graph_generate → END
      ├─ search → search_node → spark_summary → END（无图谱）
      ├─ search+graph → search_node → knowledge_graph_generate → spark_summary(brief) → END
      ├─ attachment → attachment_answer → END（无图谱）
      ├─ attachment+graph → attachment_answer → knowledge_graph_generate → END
      ├─ attachment+search → search_node → spark_summary → END（无图谱）
      ├─ attachment+search+graph → search_node → knowledge_graph_generate → spark_summary(brief) → END
      └─ graph_only → knowledge_graph_generate → spark_summary(brief) → END

优先级：附件分析 → 搜索 → 知识图谱
图谱生成必须用户显式请求（前端按钮或文字明确要求），不自动触发。
涉及图谱时：先生成图谱，再简要总结；无图谱时：详细回答。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from app.chat.request import ChatHistoryMessage
from app.chat.schemas import ChatKnowledgeGraph, TutorAgentContext, TutorState
from app.utils.context import runtime_context as chat_runtime_context
from app.chat.runtime import prepare_tutor_state
from app.resource.utils.graph_utils import normalize_render_graph
from app.resource.graph_store import get_graph_store
from app.chat.utils import (
    classify_route,
    extract_question,
    is_unusable_reply_text,
    node_timer,
    normalize_message_content,
    stream_event,
    truncate,
    build_messages,
)
from app.config import LANGGRAPH_DEBUG
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.prompts import registry
from app.utils.search import duckduckgo_search, serp_search, tavily_search

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

logger = get_logger(__name__)


async def store_knowledge_graph(
    *,
    user_id: int,
    session_id: str,
    graph: dict[str, Any],
) -> dict[str, Any]:
    try:
        return await get_graph_store().upsert_graph(
            user_id=user_id,
            resource_id=session_id or "chat",
            agent_id="chat",
            graph=graph,
        )
    except Exception as exc:
        logger.exception("[TutorAgent] 聊天知识图谱 Neo4j 存储失败")
        return {"stored": False, "error": str(exc)}

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# LangGraph 递归限制
GRAPH_RECURSION_LIMIT = 30
# 图节点名称集合
GRAPH_NODE_NAMES = {
    "classify",
    "direct_answer",
    "search_node",
    "spark_summary",
    "attachment_answer",
    "knowledge_graph_generate",
}
# 回答节点名称集合（会发送 token 事件）
ANSWER_NODE_NAMES = {"direct_answer", "spark_summary", "attachment_answer"}


def _get_prompt(name: str) -> str:
    """获取聊天模块的 prompt 文本。"""
    return registry.get(f"chat/{name}")


def _graph_stream_kwargs() -> dict[str, Any]:
    """构建 LangGraph 流式参数。

    Returns:
        包含 version、config、debug 的参数字典。
    """
    kwargs: dict[str, Any] = {
        "version": "v2",
        "config": {"recursion_limit": GRAPH_RECURSION_LIMIT},
    }
    if LANGGRAPH_DEBUG:
        kwargs["debug"] = True
    return kwargs


def _stream_chunk_text(chunk: Any) -> str:
    """从 LangChain 流式块中提取纯文本。

    Args:
        chunk: LangChain 流式块对象。

    Returns:
        提取的纯文本字符串。
    """
    if chunk is None:
        return ""
    content = getattr(chunk, "content", chunk)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return ""


class Intent(BaseModel):
    """用户意图分类。"""
    search: bool = Field(description="是否需要使用联网搜索工具获取最新信息或文档")
    graph: bool = Field(description="用户是否显式要求生成知识图谱（前端按钮或文字明确请求）")


class TutorAgent:
    """智能辅导 Agent — 轻量级编排器。

    三种对话路径：
    1. direct_answer — Spark MAX 直接回答，无工具
    2. search_node → spark_summary — Spark MAX 搜索后 Spark MAX 总结
    3. attachment_answer — Spark MAX 基于附件分析结果回答
    """

    def __init__(self, context: TutorAgentContext) -> None:
        """初始化 TutorAgent。

        创建 LLM 实例、保存服务层构造好的上下文、初始化图。
        """
        self.context = context
        # LLM 实例
        self.llm = get_llm()

        # 图与工具
        self.graph = None
        self._init_lock = asyncio.Lock()
        self._background_tasks: set[asyncio.Task] = set()

        logger.info("[TutorAgent] 初始化完成")

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------

    async def _invoke_with_retry(
        self,
        messages: list[Any],
        *,
        node_name: str,
        fallback_text: str = "抱歉，我暂时无法回答这个问题，请稍后重试。",
        retry_prompt: str = "请重新回答用户问题，给出完整、可读、适合教学场景的中文回答。",
    ) -> str:
        """调用 LLM 并在无效回复时重试。

        Args:
            messages: 初始消息列表。
            node_name: 节点名称，用于日志。
            fallback_text: 最终失败时的回退文本。
            retry_prompt: 重试时的提示词。

        Returns:
            LLM 返回的文本内容。
        """
        try:
            response = await self.llm.ainvoke(
                messages,
                temperature=1.0,
            )
            text = normalize_message_content(getattr(response, "content", response))
        except Exception as exc:
            logger.warning("[TutorAgent] %s Spark MAX 调用失败 err=%s", node_name, exc)
            text = ""

        # 无效回复重试
        if is_unusable_reply_text(text):
            logger.warning("[TutorAgent] %s 重试 原因=无效回复", node_name)
            retry_messages = messages + [HumanMessage(content=retry_prompt)]
            try:
                retry_response = await self.llm.ainvoke(
                    retry_messages,
                    temperature=1.0,
                )
                text = normalize_message_content(getattr(retry_response, "content", retry_response))
            except Exception as exc:
                logger.warning("[TutorAgent] %s 重试调用失败 err=%s", node_name, exc)
                text = ""

        if is_unusable_reply_text(text):
            text = fallback_text

        return text

    # ------------------------------------------------------------------
    # 图构建
    # ------------------------------------------------------------------

    async def _ensure_graph(self) -> None:
        """构建 LangGraph 状态图。

        定义节点和边，编译为可执行图。
        """
        if self.graph is not None:
            return

        async with self._init_lock:
            if self.graph is not None:
                return

            # 创建状态图
            graph = StateGraph(TutorState)
            # 添加节点
            graph.add_node("classify", self._classify_node)
            graph.add_node("direct_answer", self._direct_answer_node)
            graph.add_node("search_node", self._search_node)
            graph.add_node("spark_summary", self._spark_summary_node)
            graph.add_node("attachment_answer", self._attachment_answer_node)
            graph.add_node("knowledge_graph_generate", self._knowledge_graph_generate_node)

            # 添加边
            graph.add_edge(START, "classify")
            graph.add_conditional_edges(
                "classify",
                classify_route,
                {
                    "direct": "direct_answer",
                    "direct_graph": "direct_answer",
                    "search": "search_node",
                    "search_graph": "search_node",
                    "attachment_needed": "attachment_answer",
                    "attachment_graph": "attachment_answer",
                    "graph_only": "knowledge_graph_generate",
                },
            )
            # direct_answer 后：有图谱 → knowledge_graph_generate，无图谱 → END
            graph.add_conditional_edges(
                "direct_answer",
                self._route_after_answer,
                {
                    "kg": "knowledge_graph_generate",
                    "end": END,
                },
            )
            # search_node 后：有图谱 → knowledge_graph_generate，无图谱 → spark_summary
            graph.add_conditional_edges(
                "search_node",
                self._route_after_search,
                {
                    "kg": "knowledge_graph_generate",
                    "summary": "spark_summary",
                },
            )
            # attachment_answer 后：有图谱 → knowledge_graph_generate，无图谱 → END
            graph.add_conditional_edges(
                "attachment_answer",
                self._route_after_answer,
                {
                    "kg": "knowledge_graph_generate",
                    "end": END,
                },
            )
            # knowledge_graph_generate 后：需要简要总结 → spark_summary，否则 → END
            graph.add_conditional_edges(
                "knowledge_graph_generate",
                self._route_after_kg,
                {
                    "brief_summary": "spark_summary",
                    "end": END,
                },
            )
            graph.add_edge("spark_summary", END)

            self.graph = graph.compile()

    # ------------------------------------------------------------------
    # 条件路由
    # ------------------------------------------------------------------

    @staticmethod
    def _route_after_answer(state: dict) -> str:
        """direct_answer / attachment_answer 后的路由：有图谱需求 → kg，否则结束。"""
        route = state.get("route", "")
        if "graph" in route:
            return "kg"
        return "end"

    @staticmethod
    def _route_after_search(state: dict) -> str:
        """search_node 后的路由：有图谱需求 → kg，否则 → spark_summary。"""
        route = state.get("route", "")
        if "graph" in route:
            return "kg"
        return "summary"

    @staticmethod
    def _route_after_kg(state: dict) -> str:
        """knowledge_graph_generate 后的路由：需要简要总结 → spark_summary，否则结束。

        search+graph 和 graph_only 路径需要 spark_summary 简要总结。
        direct+graph 和 attachment+graph 路径前面已有详细回答，直接结束。
        """
        if state.get("summary_type") == "brief":
            return "brief_summary"
        return "end"

    # ------------------------------------------------------------------
    # 节点: classify
    # ------------------------------------------------------------------

    async def _classify_node(self, state: TutorState) -> dict[str, Any]:
        """分类节点：根据用户意图和显式请求决定路由。

        路由规则：
        - 图谱必须用户显式请求（前端按钮 need_knowledge_graph 或文字明确要求）
        - 优先级：附件分析 → 搜索 → 知识图谱
        - 有图谱时：search+graph 走 search→kg→summary(brief)，
          graph_only 走 kg→summary(brief)，其他有图谱路径先回答再生成图谱
        """
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        messages = state.get("messages") or []
        file_urls = state.get("file_urls") or []
        image_urls = state.get("image_urls") or []
        messages = state.get("messages") or []
        enable_search = bool(state.get("enable_search", False))
        need_knowledge_graph = bool(state.get("need_knowledge_graph", False))
        user_message = extract_question(messages)
        recent_chat_context = str(state.get("recent_chat_context", "")).strip()

        has_attachments = bool(file_urls or image_urls)

        with node_timer("classify", user=user_id, session=session_id):
            # 动态意图分类（仅判断 search 和 graph）
            intent_graph = False
            try:
                classify_prompt = _get_prompt("intent_classify")
                prompt_content = f"用户最新问题：\n{user_message}\n\n近期对话上下文：\n{recent_chat_context}"
                intent = await self.llm.ainvoke_json(
                    Intent,
                    [
                        SystemMessage(content=classify_prompt),
                        HumanMessage(content=prompt_content),
                    ],
                    temperature=0.1,
                )
                if intent.search:
                    enable_search = True
                if intent.graph:
                    intent_graph = True
            except Exception as exc:
                logger.warning("[TutorAgent] 意图分类失败，降级为默认参数 err=%s", exc)

            # 图谱需求：前端显式按钮 或 文字明确要求（二者取其一即可）
            need_kg = need_knowledge_graph or intent_graph

            # 构造 state_updates
            state_updates: dict[str, Any] = {}
            current_need_kg = state.get("need_knowledge_graph")
            if current_need_kg is not None and need_kg != current_need_kg:
                state_updates["need_knowledge_graph"] = need_kg

            # 路由决策
            if need_kg:
                # --- 有图谱需求的路径 ---
                if enable_search:
                    # search+graph: search → kg → spark_summary(brief)
                    route = "search_graph"
                    execution_mode = "search_graph"
                    summary_type = "brief"
                elif has_attachments:
                    # attachment+graph: attachment_answer → kg → END（前面已有详细回答）
                    route = "attachment_graph"
                    execution_mode = "attachment_graph"
                    summary_type = None
                else:
                    # graph_only: kg → spark_summary(brief)
                    route = "graph_only"
                    execution_mode = "graph_only"
                    summary_type = "brief"
            else:
                # --- 无图谱需求的路径 ---
                if enable_search:
                    route = "search"
                    execution_mode = "attachment_search" if has_attachments else "search"
                    summary_type = None
                elif has_attachments:
                    route = "attachment_needed"
                    execution_mode = "attachment"
                    summary_type = None
                else:
                    route = "direct"
                    execution_mode = "direct"
                    summary_type = None

            logger.debug(
                "[TutorAgent] 路由分类 route=%s execution_mode=%s need_kg=%s question=%s",
                route,
                execution_mode,
                need_kg,
                truncate(user_message, 120),
            )

            state_updates.update({
                "route": route,
                "execution_mode": execution_mode,
            })
            if summary_type:
                state_updates["summary_type"] = summary_type
            if enable_search != bool(state.get("enable_search", False)):
                state_updates["enable_search"] = True

            return state_updates

    # ------------------------------------------------------------------
    # 节点: direct_answer
    # ------------------------------------------------------------------

    async def _direct_answer_node(self, state: TutorState) -> dict[str, Any]:
        """直接回答路径：Spark MAX 直接回答，不调用工具。

        Args:
            state: LangGraph 状态。

        Returns:
            更新后的状态片段。
        """
        messages = state.get("messages") or []
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        system_prompt = state.get("system_prompt", "")
        question = extract_question(messages)

        with node_timer("direct_answer", user=user_id, session=session_id):
            logger.debug("[TutorAgent] 直接回答：question=%s", truncate(question, 180))

            full_messages = build_messages(system_prompt, list(messages))
            text = await self._invoke_with_retry(full_messages, node_name="direct_answer")

            response_msg = AIMessage(content=text)
            logger.debug("[TutorAgent] direct_answer 完成 preview=%s", truncate(text, 220))

            return {
                "messages": [response_msg],
                "answer_text": text,
                "termination_reason": "direct_answer_done",
            }


    async def _search_node(self, state: TutorState) -> dict[str, Any]:
        """搜索节点：Spark MAX 使用搜索工具查找信息。

        Args:
            state: LangGraph 状态。

        Returns:
            更新后的状态片段，包含 search_result。
        """
        messages = state.get("messages") or []
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        system_prompt = state.get("system_prompt", "")
        question = extract_question(messages)
        attachment_context = str(state.get("attachment_analysis_context", "")).strip()

        with node_timer("search_node", user=user_id, session=session_id):
            logger.info("[TutorAgent] 搜索节点 question=%s", truncate(question, 180))

            search_instruction = HumanMessage(
                content=(
                    "请根据用户最新问题调用搜索工具查找必要信息，只整理与问题直接相关的事实、"
                    "来源线索和不足之处。若本轮包含附件预分析上下文，请围绕附件内容和用户问题补充检索。"
                    "不要生成最终教学回答。"
                    + (
                        f"\n\n附件预分析上下文：\n{attachment_context}"
                        if attachment_context
                        else ""
                    )
                )
            )
            full_messages = build_messages(system_prompt, list(messages) + [search_instruction])

            # 绑定搜索工具
            llm_with_tools = self.llm.model.bind_tools(
                [duckduckgo_search, tavily_search, serp_search],
            )

            try:
                response = await self.llm.ainvoke(full_messages, model=llm_with_tools)
            except Exception:
                logger.exception("[TutorAgent] search_node Spark MAX 调用失败")
                raise

            # 处理工具调用
            search_result = normalize_message_content(getattr(response, "content", response))

            # 如果有工具调用，执行它们
            tool_calls = getattr(response, "tool_calls", [])
            if tool_calls:
                tool_results = []
                for tool_call in tool_calls:
                    tool_name = tool_call.get("name", "")
                    tool_args = tool_call.get("args", {})
                    try:
                        if tool_name == "duckduckgo_search":
                            result = await duckduckgo_search.ainvoke(tool_args)
                        elif tool_name == "tavily_search":
                            result = await tavily_search.ainvoke(tool_args)
                        elif tool_name == "serp_search":
                            result = await serp_search.ainvoke(tool_args)
                        else:
                            result = ""
                        tool_results.append(f"【{tool_name}】\n{result}")
                    except Exception as exc:
                        logger.warning("[TutorAgent] 搜索工具 %s 失败: %s", tool_name, exc)
                        tool_results.append(f"【{tool_name}】搜索失败")

                search_result = search_result + "\n\n" + "\n\n".join(tool_results)

            logger.debug("[TutorAgent] search_node 完成 preview=%s", truncate(search_result, 220))

            return {
                "search_result": search_result,
                "termination_reason": "search_done",
            }


    async def _spark_summary_node(self, state: TutorState) -> dict[str, Any]:
        """Spark 总结节点：基于参考资料生成教学回答。

        支持两种模式：
        - detailed（默认）：基于搜索结果详细回答
        - brief：基于知识图谱数据简要总结（1-3句话）
        """
        messages = state.get("messages") or []
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        search_result = state.get("search_result", "")
        system_prompt = state.get("system_prompt", "")
        question = extract_question(messages)
        summary_type = state.get("summary_type")

        with node_timer("spark_summary", user=user_id, session=session_id):
            logger.debug("[TutorAgent] Spark 总结 question=%s summary_type=%s", truncate(question, 180), summary_type)

            # 构建参考资料
            reference = search_result
            if not reference and state.get("knowledge_graph"):
                reference = json.dumps(state["knowledge_graph"], ensure_ascii=False, default=str)

            if summary_type == "brief":
                prompt = (
                    f"用户问题：{question}\n\n"
                    f"参考资料（知识图谱数据）：\n{reference}\n\n"
                    "请基于以上知识图谱数据，用 1-3 句话简要总结核心概念和关键关系，"
                    "帮助用户快速理解图谱内容。不要重复罗列所有节点，只提炼最重要的信息。"
                )
                fallback_text = "知识图谱已生成，请查看上方可视化展示。"
                retry_prompt = "请用 1-3 句话简要总结知识图谱的核心内容。"
            else:
                prompt = (
                    f"用户问题：{question}\n\n"
                    f"参考资料：\n{reference}\n\n"
                    "请结合参考资料直接回答用户问题。语言自然、清晰、有教学价值。注意：绝对不要在回答中提及「根据参考资料」、「搜索结果表明」等任何揭示你进行了检索的词语，要表现得就如同你原本就知道这些知识一样。"
                )
                fallback_text = search_result or "抱歉，我暂时无法回答这个问题，请稍后重试。"
                retry_prompt = "请基于搜索结果重新回答，给出完整、可读、适合教学场景的中文回答。"

            full_messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt),
            ]

            text = await self._invoke_with_retry(
                full_messages,
                node_name="spark_summary",
                fallback_text=fallback_text,
                retry_prompt=retry_prompt,
            )

            response_msg = AIMessage(content=text)
            logger.debug("[TutorAgent] spark_summary 完成 preview=%s", truncate(text, 220))

            return {
                "messages": [response_msg],
                "answer_text": text,
                "termination_reason": "spark_summary_done",
            }


    async def _attachment_answer_node(self, state: TutorState) -> dict[str, Any]:
        """附件理解路径：Spark MAX 基于附件预分析结果回答。

        Args:
            state: LangGraph 状态。

        Returns:
            更新后的状态片段。
        """
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        file_urls = state.get("file_urls") or []
        image_urls = state.get("image_urls") or []
        messages = list(state.get("messages") or [])
        question = extract_question(messages)
        pre_analysis = state.get("attachment_analysis") or {}
        system_prompt = state.get("system_prompt", "")

        with node_timer(
            "attachment_answer",
            user=user_id,
            session=session_id,
            image_count=len(image_urls),
            file_count=len(file_urls),
        ):
            logger.info(
                "[TutorAgent] 附件回答 route=attachment_answer question=%s images=%s files=%s",
                truncate(question, 180),
                len(image_urls),
                len(file_urls),
            )

            # 获取附件分析上下文
            full_context = str(state.get("attachment_analysis_context", "")).strip()
            if not full_context and isinstance(pre_analysis, dict):
                full_context = str(pre_analysis.get("analysis_context", "")).strip()

            if not full_context:
                full_context = (
                    "本轮包含附件，但上传阶段未返回可用的附件预分析结果。"
                    "请基于用户问题说明目前无法可靠读取附件内容，并建议用户重新上传或稍后重试。"
                )

            # 构建回答提示词
            answer_prompt = (
                f"用户问题: {question}\n\n"
                f"以下是上传阶段已经完成的附件预分析内容：\n{full_context}\n\n"
                "请只根据这些预分析内容和已有对话回答用户问题，不要尝试读取附件、调用文件工具或重新分析图片。"
                "如果内容不足以回答问题，请明确说明缺失点；"
                "回答要清晰、分点、适合教学场景。"
            )

            full_messages = build_messages(system_prompt, [HumanMessage(content=answer_prompt)])

            text = await self._invoke_with_retry(full_messages, node_name="attachment_answer")

            response_msg = AIMessage(content=text)
            logger.debug("[TutorAgent] attachment_answer 完成 preview=%s", truncate(text, 220))

            return {
                "messages": [response_msg],
                "answer_text": text,
                "attachment_analysis_result": {
                    "mode": "upload_preanalysis",
                    "analysis_context": full_context,
                },
                "termination_reason": "attachment_answer_done",
            }

    async def _knowledge_graph_generate_node(self, state: TutorState) -> TutorState:
        """知识图谱生成节点；失败时仅跳过图谱。

        支持两种输入：
        - 有 answer_text（direct/attachment 路径）：基于回答生成图谱
        - 有 search_result（search+graph 路径）：基于搜索结果生成图谱
        - 仅有 question（graph_only 路径）：直接基于问题生成图谱
        """
        user_id = int(state.get("user_id") or 0)
        session_id = str(state.get("session_id") or "")
        with node_timer("knowledge_graph_generate", user=user_id, session=session_id):
            try:
                question = extract_question(state.get("messages") or [])

                # 收集可用上下文：优先 answer_text，其次 search_result
                answer = ""
                for key in ("final_answer", "answer_text", "answer", "response"):
                    value = state.get(key)  # type: ignore[literal-required]
                    if value:
                        answer = normalize_message_content(value)
                        break
                if not answer:
                    final_ai = next(
                        (
                            msg
                            for msg in reversed(state.get("messages") or [])
                            if isinstance(msg, AIMessage)
                        ),
                        None,
                    )
                    answer = normalize_message_content(final_ai.content if final_ai else "")

                # search+graph 路径：搜索结果作为补充上下文
                search_result = state.get("search_result", "")
                if search_result and not answer:
                    answer = f"搜索参考资料：\n{search_result}"
                elif search_result and answer:
                    answer = f"{answer}\n\n搜索参考资料：\n{search_result}"

                if not question:
                    state["knowledge_graph"] = None
                    state["knowledge_graph_error"] = "缺少问题，跳过知识图谱生成"
                    return state

                if not answer:
                    answer = "用户要求直接生成图谱，无大模型文本回答。请直接基于上述问题构建知识图谱。"

                state["knowledge_graph"] = await self._generate_knowledge_graph(
                    question=question,
                    answer=answer,
                    state=state,
                )
                return state
            except Exception as exc:
                logger.exception("[TutorAgent] 知识图谱节点失败")
                state["knowledge_graph"] = None
                state["knowledge_graph_error"] = str(exc)
                return state

    async def _generate_knowledge_graph(
        self,
        *,
        question: str,
        answer: str,
        state: TutorState,
    ) -> dict[str, Any] | None:
        """调用 LLM 生成知识图谱 JSON 并持久化到 Neo4j。

        Args:
            question: 用户问题。
            answer: 大模型回答或搜索结果文本。
            state: 当前 LangGraph 状态，用于提取上下文和用户信息。

        Returns:
            归一化后的图谱数据字典，失败时返回 None。
        """
        profile_context = str(state.get("profile_context", "")).strip()
        fact_context = str(state.get("fact_context", "")).strip()
        recent_chat_context = str(state.get("recent_chat_context", "")).strip()
        attachment_context = str(state.get("attachment_analysis_context", "")).strip()
        context_parts = []
        if profile_context:
            context_parts.append(f"用户画像上下文：\n{profile_context}")
        if fact_context:
            context_parts.append(f"长期记忆上下文：\n{fact_context}")
        if recent_chat_context:
            context_parts.append(f"近期对话上下文：\n{recent_chat_context}")
        if attachment_context:
            context_parts.append(f"附件预分析上下文：\n{attachment_context}")

        prompt = (
            f"学生问题：\n{question}\n\n"
            f"最终回答：\n{answer}\n\n"
            f"上下文：\n{chr(10).join(context_parts) if context_parts else '无额外上下文。'}\n\n"
            "请生成适合 Neo4j 与前端关系图渲染的知识图谱 JSON。"
            "节点必须是原子知识点，优先 6 到 14 个节点；"
            "关系只能使用 prerequisite、extends、includes、related；"
            "不要输出 Mermaid，不要输出 Markdown。"
        )
        payload = await self.llm.ainvoke_json(
            ChatKnowledgeGraph,
            [
                SystemMessage(content=_get_prompt("knowledge_graph")),
                HumanMessage(content=prompt),
            ],
            temperature=0.1,
        )

        graph = normalize_render_graph(
            payload.model_dump(mode="json"),
            layout_mode="force",
            relation_depth=2,
        )

        graph["neo4j"] = await store_knowledge_graph(
            user_id=int(state.get("user_id") or 0),
            session_id=str(state.get("session_id") or "chat"),
            graph=graph,
        )
        return graph

    # ------------------------------------------------------------------
    # 后台任务
    # ------------------------------------------------------------------

    def _spawn_background(self, coro: Any, *, task_name: str) -> None:
        """安全启动后台任务。

        Args:
            coro: 协程对象。
            task_name: 任务名称。
        """
        task = asyncio.create_task(coro, name=task_name)
        self._background_tasks.add(task)

        def _done_callback(done_task: asyncio.Task) -> None:
            """任务完成回调，清理任务集合并记录异常。"""
            self._background_tasks.discard(done_task)
            if done_task.cancelled():
                return
            try:
                done_task.result()
            except Exception:
                logger.exception("[TutorAgent] 后台任务异常 task=%s", task_name)

        task.add_done_callback(_done_callback)

    # ------------------------------------------------------------------
    # 主入口：SSE 流式对话
    # ------------------------------------------------------------------

    async def chat_stream(
        self,
        history: list[ChatHistoryMessage],
    ):
        """流式生成对话响应。

        TutorAgent 是无状态决策层：只消费初始化上下文和本轮传入的历史，不读写记忆。

        Args:
            history: 调用方传入的完整对话历史，最后一条用户消息是本轮问题。

        Yields:
            SSE 事件字典。
        """
        context = self.context
        current_message = ""
        for item in reversed(history):
            if item.role == "user" and item.content.strip():
                current_message = item.content.strip()
                break

        resource_requested = bool(context.resource_mode and context.resource_mode != "none") or context.generate_video
        if resource_requested:
            logger.info("[TutorAgent] 当前版本仅生成文字回答，已忽略多模态资源请求")

        logger.info(
            "[TutorAgent] 对话开始 message=%s attachments(images=%s,files=%s) enable_search=%s",
            truncate(current_message, 180),
            len(context.image_urls),
            len(context.file_urls),
            context.enable_search,
        )

        await self._ensure_graph()

        initial_state = prepare_tutor_state(context, history)

        full_reply = ""
        runtime_state: dict[str, Any] = dict(initial_state)
        graph_error_text = ""
        active_node = ""

        try:
            # 在上下文中运行图
            with chat_runtime_context(context.user_id, context.session_id):
                async for event in self.graph.astream_events(initial_state, **_graph_stream_kwargs()):
                    kind = event.get("event", "")
                    name = event.get("name", "")

                    # 节点开始事件
                    if kind == "on_chain_start" and name in GRAPH_NODE_NAMES:
                        active_node = name
                        if name in ANSWER_NODE_NAMES:
                            yield stream_event(
                                "status",
                                {
                                    "stage": name,
                                    "message": "正在检索和组织答案，请稍候...",
                                },
                            )
                        elif name == "knowledge_graph_generate":
                            yield stream_event(
                                "status",
                                {
                                    "stage": name,
                                    "message": "正在生成知识图谱...",
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

                    # LLM 实时流式输出：前端收到每个 chunk 后逐步追加显示。
                    if kind == "on_chat_model_stream":
                        metadata = event.get("metadata") or {}
                        node_name = metadata.get("langgraph_node") or active_node
                        if node_name in ANSWER_NODE_NAMES:
                            chunk_text = _stream_chunk_text(event.get("data", {}).get("chunk"))
                            if chunk_text:
                                full_reply += chunk_text
                                yield stream_event("token", chunk_text)

                    # 兼容未产生流式 chunk 的模型/路径，避免前端空白。
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
                                    full_reply = final_text
                                    yield stream_event("token", final_text)

        except Exception as exc:
            logger.exception("[TutorAgent] 请求异常")
            graph_error_text = f"服务器出错: {exc}"

        logger.info(
            "[TutorAgent] 请求结束 termination_reason=%s",
            runtime_state.get("termination_reason", ""),
        )

        # 发送错误事件
        if graph_error_text:
            yield stream_event("error", graph_error_text)
            yield stream_event("done", {"session_id": context.session_id, "error": True})
            return

        # 从状态中提取回复
        if not full_reply:
            messages = runtime_state.get("messages", [])
            if isinstance(messages, list):
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage):
                        full_reply = normalize_message_content(msg.content)
                        break

        # 检查无效回复
        if is_unusable_reply_text(full_reply):
            yield stream_event("error", "模型未返回有效内容，请重试。")
            yield stream_event("done", {"session_id": context.session_id, "error": True})
            return

        # 发送完成事件
        yield stream_event(
            "done",
            {
                "session_id": context.session_id,
                "full_response": full_reply,
                "resource_mode": "none",
                "resource": None,
                "resources": {
                    "knowledge_graph": runtime_state.get("knowledge_graph"),
                    "video": None,
                },
            },
        )
