# -*- coding: utf-8 -*-
"""TutorAgent: 轻量级教育场景编排器。

当前工作流：
    START -> classify
      ├─ direct_answer (Spark MAX 直接回答) -> diagram_generate -> END
      ├─ search_node (Spark MAX 搜索，可结合附件预分析上下文) -> spark_summary -> diagram_generate -> END
      └─ attachment_answer (Spark MAX 总结) -> diagram_generate -> END

职责：
- 接收请求
- 识别问题应该走哪条回答路径
- 调用对应的回答能力
- 返回统一响应
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Optional

from app.utils.mermaid import build_mermaid_render
from app.chat.schemas import DIAGRAM_MODEL_MAP, DiagramDecision, TutorState
from app.utils.json import parse_first_json_object
from app.utils.context import runtime_context as chat_runtime_context
from app.utils.paths import CHAT_DIR
from app.chat.runtime import build_user_message_record, prepare_tutor_turn, resolve_session_id
from app.chat.utils import (
    classify_route,
    extract_question,
    is_unusable_reply_text,
    load_prompts,
    node_timer,
    normalize_message_content,
    stream_event,
    truncate,
    build_messages,
)
from app.config import LANGGRAPH_DEBUG
from app.memory import MemoryLayer
from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.utils.search import duckduckgo_search, serp_search, tavily_search

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# Agent 所在目录
AGENT_DIR = Path(__file__).resolve().parent
# LangGraph 递归限制
GRAPH_RECURSION_LIMIT = 30
# 图节点名称集合
GRAPH_NODE_NAMES = {
    "classify",
    "direct_answer",
    "search_node",
    "spark_summary",
    "attachment_answer",
    "diagram_generate",
}
# 回答节点名称集合（会发送 token 事件）
ANSWER_NODE_NAMES = {"direct_answer", "spark_summary", "attachment_answer"}

# ---------------------------------------------------------------------------
# Prompt 加载
# ---------------------------------------------------------------------------

# 加载提示词区段
PROMPTS: dict[str, str] = load_prompts(AGENT_DIR)


def _get_prompt(name: str) -> str:
    """获取提示词，如果不存在返回空字符串。

    Args:
        name: 提示词名称。

    Returns:
        提示词内容。
    """
    return PROMPTS.get(name, "")


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


class TutorAgent:
    """智能辅导 Agent — 轻量级编排器。

    三种对话路径：
    1. direct_answer — Spark MAX 直接回答，无工具
    2. search_node → spark_summary — Spark MAX 搜索后 Spark MAX 总结
    3. attachment_answer — Spark MAX 基于附件分析结果回答
    """

    # 单例实例
    _shared_instance: "TutorAgent | None" = None

    def __init__(self) -> None:
        """初始化 TutorAgent。

        创建 LLM 实例、上下文服务、图和工具。
        """
        # LLM 实例
        self.llm_manager = get_llm_manager()
        self.spark_model_kwargs = {"temperature": 1.0, "streaming": True}
        self.search_model_kwargs = {"temperature": 0.1, "streaming": False, "max_tokens": 1200}
        self.diagram_model_kwargs = {"temperature": 0.1, "streaming": False, "max_tokens": 1600}
        # 上下文服务
        self.memory_layer = MemoryLayer(module="mentor")

        # 图与工具
        self.graph = None
        self._init_lock = asyncio.Lock()
        self._background_tasks: set[asyncio.Task] = set()

        logger.info("[TutorAgent] 初始化完成")

    @classmethod
    def get_shared(cls) -> "TutorAgent":
        """获取全局单例。

        Returns:
            TutorAgent 单例实例。
        """
        if cls._shared_instance is None:
            cls._shared_instance = cls()
        return cls._shared_instance

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
            response = await self.llm_manager.ainvoke(
                "spark_max",
                messages,
                model_kwargs=self.spark_model_kwargs,
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
                retry_response = await self.llm_manager.ainvoke(
                    "spark_max",
                    retry_messages,
                    model_kwargs=self.spark_model_kwargs,
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
            graph.add_node("diagram_generate", self._diagram_generate_node)

            # 添加边
            graph.add_edge(START, "classify")
            graph.add_conditional_edges(
                "classify",
                classify_route,
                {
                    "direct": "direct_answer",
                    "search": "search_node",
                    "attachment_needed": "attachment_answer",
                },
            )
            graph.add_edge("direct_answer", "diagram_generate")
            graph.add_edge("search_node", "spark_summary")
            graph.add_edge("spark_summary", "diagram_generate")
            graph.add_edge("attachment_answer", "diagram_generate")
            graph.add_edge("diagram_generate", END)

            self.graph = graph.compile()

    # ------------------------------------------------------------------
    # 节点: classify
    # ------------------------------------------------------------------

    async def _classify_node(self, state: TutorState) -> dict[str, Any]:
        """分类节点：区分 direct / search / attachment_needed。

        路由规则：
        1. 启用搜索 → search_node（可同时结合附件预分析上下文）
        2. 有附件 → attachment_answer
        3. 无附件 + 无搜索 → direct_answer

        Args:
            state: LangGraph 状态。

        Returns:
            更新后的状态片段。
        """
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        messages = state.get("messages") or []
        file_urls = state.get("file_urls") or []
        image_urls = state.get("image_urls") or []
        resource_mode = state.get("resource_mode", "none")
        enable_search = bool(state.get("enable_search", False))
        user_message = extract_question(messages)

        with node_timer("classify", user=user_id, session=session_id):
            # 路径1：搜索优先，支持与附件预分析上下文组合
            if enable_search:
                execution_mode = "attachment_search" if (file_urls or image_urls) else "search"
                logger.debug(
                    "[TutorAgent] 路由分类 route=search reason=enable_search question=%s attachments(images=%s,files=%s)",
                    truncate(user_message, 120),
                    len(image_urls),
                    len(file_urls),
                )
                return {"route": "search", "execution_mode": execution_mode}

            # 路径2：仅附件
            if file_urls or image_urls:
                logger.debug(
                    "[TutorAgent] 路由分类 route=attachment_needed reason=attachments_present images=%s files=%s resource_mode=%s",
                    len(image_urls),
                    len(file_urls),
                    resource_mode,
                )
                return {"route": "attachment_needed", "execution_mode": "attachment"}

            # 路径3：直接回答
            logger.debug(
                "[TutorAgent] 路由分类 route=direct reason=no_attachments_no_search question=%s",
                truncate(user_message, 120),
            )
            return {"route": "direct", "execution_mode": "direct"}

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

    # ------------------------------------------------------------------
    # 节点: search_node
    # ------------------------------------------------------------------

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
            llm_with_tools = self.llm_manager.bind_tools(
                "spark_max",
                [duckduckgo_search, tavily_search, serp_search],
                model_kwargs=self.search_model_kwargs,
            )

            try:
                response = await self.llm_manager.ainvoke_runnable(
                    llm_with_tools,
                    full_messages,
                    model_type="spark_max",
                )
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

    # ------------------------------------------------------------------
    # 节点: spark_summary
    # ------------------------------------------------------------------

    async def _spark_summary_node(self, state: TutorState) -> dict[str, Any]:
        """Spark 总结节点：基于搜索结果生成教学回答。

        Args:
            state: LangGraph 状态。

        Returns:
            更新后的状态片段。
        """
        messages = state.get("messages") or []
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        search_result = state.get("search_result", "")
        system_prompt = state.get("system_prompt", "")
        question = extract_question(messages)

        with node_timer("spark_summary", user=user_id, session=session_id):
            logger.debug("[TutorAgent] Spark 总结 question=%s", truncate(question, 180))

            prompt = (
                f"用户问题：{question}\n\n"
                f"搜索结果：\n{search_result}\n\n"
                "请基于搜索结果回答用户问题，语言自然、清晰、有教学价值。"
            )

            full_messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt),
            ]

            text = await self._invoke_with_retry(
                full_messages,
                node_name="spark_summary",
                fallback_text=search_result or "抱歉，我暂时无法回答这个问题，请稍后重试。",
                retry_prompt="请基于搜索结果重新回答，给出完整、可读、适合教学场景的中文回答。",
            )

            response_msg = AIMessage(content=text)
            logger.debug("[TutorAgent] spark_summary 完成 preview=%s", truncate(text, 220))

            return {
                "messages": [response_msg],
                "answer_text": text,
                "termination_reason": "spark_summary_done",
            }

    # ------------------------------------------------------------------
    # 节点: attachment_answer
    # ------------------------------------------------------------------

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

    async def _decide_diagram(
        self,
        *,
        question: str,
        answer: str,
        state: TutorState,
    ) -> DiagramDecision:
        """判断是否需要为最终回答生成图解。

        Args:
            question: 用户问题。
            answer: 最终回答文本。
            state: LangGraph 状态。

        Returns:
            图解决策结果。
        """
        requested = state.get("need_diagram")
        if requested is False:
            return DiagramDecision(
                need_diagram=False,
                diagram_type=None,
                reason="diagram_disabled_by_user",
            )

        prompt = (
            f"User question:\n{question}\n\n"
            f"Final answer:\n{answer}\n\n"
            f"User explicitly requests diagram: {bool(requested)}\n\n"
            "Decide whether to generate a diagram and choose the best diagram_type."
        )

        try:
            decision = await self._ainvoke_diagram_model(
                DiagramDecision,
                [
                    SystemMessage(content=_get_prompt("diagram_decision_system")),
                    HumanMessage(content=prompt),
                ],
            )

            if requested is True and decision.need_diagram and not decision.diagram_type:
                return DiagramDecision(
                    need_diagram=True,
                    diagram_type="flow",
                    reason=decision.reason or "fallback_flow_for_requested_diagram",
                )

            if decision.diagram_type not in DIAGRAM_MODEL_MAP:
                if not decision.need_diagram:
                    return decision
                return DiagramDecision(
                    need_diagram=False,
                    diagram_type=None,
                    reason="diagram_type_not_supported",
                )

            if not decision.need_diagram:
                return decision
            return decision
        except Exception as exc:
            logger.warning("[TutorAgent] diagram decision failed: %s", exc)
            if requested is True:
                return DiagramDecision(
                    need_diagram=True,
                    diagram_type="flow",
                    reason="fallback_flow_after_decision_error",
                )
            return DiagramDecision(
                need_diagram=False,
                diagram_type=None,
                reason="diagram_decision_failed",
            )

    async def _ainvoke_diagram_model(
        self,
        model_cls: type[Any],
        messages: list[Any],
    ) -> Any:
        """使用 Spark MAX strict function calling 调用图解模型并本地校验。

        Args:
            model_cls: Pydantic 模型类。
            messages: 消息列表。

        Returns:
            验证后的模型实例。
        """
        try:
            validated = await self.llm_manager.ainvoke_structured(
                "spark_max",
                model_cls,
                messages,
                strict=True,
                model_kwargs=self.diagram_model_kwargs,
            )
            payload = validated.model_dump(by_alias=True)
        except Exception:
            # 兼容测试替身或历史宽松 payload，必要时退回普通 JSON 解析路径
            response = await self.llm_manager.ainvoke(
                "spark_max",
                messages,
                model_kwargs={
                    **self.diagram_model_kwargs,
                    "response_format": {"type": "json_object"},
                },
            )
            payload = parse_first_json_object(
                normalize_message_content(getattr(response, "content", response))
            )
        payload = self._normalize_diagram_payload(model_cls, payload)
        return model_cls.model_validate(payload)

    @staticmethod
    def _trim_text(value: Any, max_len: int) -> Any:
        """将文本截断到指定长度。

        Args:
            value: 要截断的值，仅字符串会被修改。
            max_len: 最大字符长度。

        Returns:
            截断后的字符串或原始值。
        """
        if not isinstance(value, str):
            return value
        value = value.strip()
        if len(value) <= max_len:
            return value
        return value[:max_len]

    @classmethod
    def _trim_mapping_fields(cls, mapping: dict[str, Any], limits: dict[str, int]) -> dict[str, Any]:
        """批量截断字典中多个字段到指定长度。

        Args:
            mapping: 包含待截断字段的字典。
            limits: 字段名到字符限制的映射。

        Returns:
            修改后的字典，字段已截断。
        """
        for key, limit in limits.items():
            if key in mapping:
                mapping[key] = cls._trim_text(mapping.get(key), limit)
        return mapping

    @classmethod
    def _normalize_diagram_payload(cls, model_cls: type[Any], payload: dict[str, Any]) -> dict[str, Any]:
        """规范化 LLM 输出以匹配本地模式预期。

        Args:
            model_cls: Pydantic 模型类，用于模式参考。
            payload: LLM 返回的原始载荷字典。

        Returns:
            规范化后的载荷，匹配预期模式。
        """
        payload = dict(payload)
        cls._trim_mapping_fields(payload, {"title": 20, "summary": 50})

        if model_cls.__name__ == "HierarchyDiagram" and "spec" not in payload:
            nodes = payload.pop("nodes", None)
            if isinstance(nodes, list) and nodes and isinstance(nodes[0], dict):
                payload["spec"] = {"root": nodes[0]}

        spec = payload.get("spec")
        if not isinstance(spec, dict):
            return payload

        if model_cls.__name__ == "HierarchyDiagram":
            def _walk(node: dict[str, Any]) -> None:
                cls._trim_mapping_fields(node, {"label": 16, "description": 40})
                children = node.get("children")
                if isinstance(children, list):
                    for child in children:
                        if isinstance(child, dict):
                            _walk(child)

            root = spec.get("root")
            if isinstance(root, dict):
                _walk(root)
            return payload

        list_field_limits = {
            "steps": {"label": 16, "description": 40},
            "nodes": {"label": 16, "description": 40},
            "states": {"label": 16, "description": 40},
            "actors": {"label": 16, "description": 40},
            "items": {"label": 16, "description": 40},
            "edges": {"label": 16, "description": 40},
            "messages": {"label": 16, "description": 40},
            "transitions": {"label": 16, "description": 40},
        }
        for field_name, limits in list_field_limits.items():
            values = spec.get(field_name)
            if isinstance(values, list):
                for item in values:
                    if isinstance(item, dict):
                        cls._trim_mapping_fields(item, limits)

        return payload

    async def _generate_diagram_by_type(
        self,
        *,
        diagram_type: str,
        question: str,
        answer: str,
        state: TutorState,
    ) -> Optional[dict[str, Any]]:
        """按已决策的类型生成前端可渲染的结构化图解。

        Args:
            diagram_type: 图解类型。
            question: 用户问题。
            answer: 最终回答。
            state: LangGraph 状态。

        Returns:
            图解数据字典，失败返回 None。
        """
        model_cls = DIAGRAM_MODEL_MAP.get(diagram_type)
        if model_cls is None:
            return None

        # 提取上下文
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

        context_text = "\n\n".join(context_parts) if context_parts else "无额外上下文。"
        prompt = (
            f"diagram_type：{diagram_type}\n\n"
            f"学生问题：\n{question}\n\n"
            f"最终文字回答：\n{answer}\n\n"
            f"上下文：\n{context_text}\n\n"
            "请直接生成指定 diagram_type 对应的 Mermaid 源码。"
            "只输出 Mermaid 源码，不要输出解释、代码围栏或对象格式。"
            "必须是完整知识图解，不是 demo；覆盖主要概念、关系、步骤、边界条件或易混点。"
            "优先拆成 8 到 18 个原子知识节点。"
        )

        try:
            response = await self.llm_manager.ainvoke(
                "spark_max",
                [
                    SystemMessage(content=_get_prompt("diagram_generation_system")),
                    HumanMessage(content=prompt),
                ],
                model_kwargs=self.diagram_model_kwargs,
            )
            mermaid_source = normalize_message_content(getattr(response, "content", response))
            rendered = {
                "type": diagram_type,
                "title": f"{diagram_type} 图解",
                "summary": "Mermaid 知识图解",
                "render": build_mermaid_render(mermaid_source),
            }

            return rendered
        except Exception as exc:
            logger.warning("[TutorAgent] 图解生成失败 type=%s error=%s", diagram_type, exc)
            return None

    async def _diagram_generate_node(self, state: TutorState) -> TutorState:
        """回答后的可选图解生成节点；失败时降级为无图解。

        Args:
            state: LangGraph 状态。

        Returns:
            更新后的状态。
        """
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        with node_timer("diagram_generate", user=user_id, session=session_id):
            try:
                question = extract_question(state.get("messages") or [])
                answer = ""
                # 从多个可能的键中提取回答
                for key in ("final_answer", "answer_text", "answer", "response"):
                    value = state.get(key)  # type: ignore[literal-required]
                    if value:
                        answer = normalize_message_content(value)
                        break
                # 从消息列表中提取最后的 AI 消息
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

                # 缺少问题或回答时跳过
                if not question or not answer:
                    state["diagram"] = None
                    state["diagram_error"] = "缺少问题或回答，跳过图解生成"
                    return state

                # 决策是否需要图解
                decision = await self._decide_diagram(
                    question=question,
                    answer=answer,
                    state=state,
                )
                if not decision.need_diagram or not decision.diagram_type:
                    state["diagram"] = None
                    return state

                # 生成图解
                diagram = await self._generate_diagram_by_type(
                    diagram_type=decision.diagram_type,
                    question=question,
                    answer=answer,
                    state=state,
                )
                state["diagram"] = diagram
                return state
            except Exception as exc:
                logger.warning("[TutorAgent] 图解节点失败: %s", exc)
                state["diagram"] = None
                state["diagram_error"] = str(exc)
                return state

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
        user_id: int,
        user_message: str,
        session_id: Optional[str] = None,
        image_urls: Optional[list[str]] = None,
        file_urls: Optional[list[str]] = None,
        need_diagram: bool = False,
        generate_video: bool = False,
        enable_search: bool = False,
        enable_long_term_memory: bool = False,
        resource_mode: Optional[str] = None,
        attachment_analysis: Optional[dict[str, Any]] = None,
    ):
        """流式生成对话响应。

        Args:
            user_id: 用户ID。
            user_message: 用户消息。
            session_id: 可选的会话ID。
            image_urls: 图片URL列表。
            file_urls: 文件URL列表。
            need_diagram: 是否生成图解。
            generate_video: 是否生成视频。
            enable_search: 是否启用搜索。
            enable_long_term_memory: 是否启用长期记忆读写。
            resource_mode: 资源模式。
            attachment_analysis: 附件预分析结果。

        Yields:
            SSE 事件字典。
        """
        requested_image_urls = image_urls or []
        requested_file_urls = file_urls or []
        resource_requested = bool(resource_mode and resource_mode != "none") or generate_video
        if resource_requested:
            logger.info("[TutorAgent] 当前版本仅生成文字回答，已忽略多模态资源请求")

        logger.info(
            "[TutorAgent] 对话开始 message=%s attachments(images=%s,files=%s) enable_search=%s",
            truncate(user_message, 180),
            len(requested_image_urls),
            len(requested_file_urls),
            enable_search,
        )

        effective_session = resolve_session_id(user_id, session_id)
        user_record = build_user_message_record(
            user_message,
            image_urls=requested_image_urls,
            file_urls=requested_file_urls,
        )

        await self._ensure_graph()

        # 保存用户消息
        try:
            await self.memory_layer.save_message(
                user_id=user_id,
                session_id=effective_session,
                role="user",
                content=user_record.content,
                attachments=user_record.attachments,
            )
        except Exception as exc:
            logger.exception("[TutorAgent] 用户消息保存失败")
            yield stream_event("error", f"保存消息失败: {exc}")
            return

        # 准备对话轮次
        prepared_turn = await prepare_tutor_turn(
            ctx_service=self.memory_layer,
            prompts=PROMPTS,
            user_id=user_id,
            user_message=user_message,
            session_id=effective_session,
            image_urls=requested_image_urls,
            file_urls=requested_file_urls,
            enable_search=enable_search,
            enable_long_term_memory=enable_long_term_memory,
            need_diagram=need_diagram,
            attachment_analysis=attachment_analysis,
        )
        initial_state = prepared_turn.initial_state

        full_reply = ""
        runtime_state: dict[str, Any] = dict(initial_state)
        graph_error_text = ""
        active_node = ""

        try:
            # 在上下文中运行图
            with chat_runtime_context(user_id, effective_session):
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
                        elif name == "diagram_generate":
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
            return

        # 保存回复
        try:
            await self.memory_layer.save_message(
                user_id=user_id,
                session_id=effective_session,
                role="assistant",
                content=full_reply,
                diagram=runtime_state.get("diagram"),
            )

            # 启动后台任务处理后续流程
            self._spawn_background(
                self.memory_layer.post_turn_pipeline(
                    user_id=user_id,
                    session_id=effective_session,
                    user_message=user_message,
                    assistant_reply=full_reply,
                    enable_long_term_memory=enable_long_term_memory,
                ),
                task_name="post_chat_pipeline",
            )
        except Exception as exc:
            logger.exception("[TutorAgent] 回复保存失败")
            yield stream_event("error", f"保存回复失败: {exc}")
            return

        # 发送完成事件
        yield stream_event(
            "done",
            {
                "session_id": effective_session,
                "resource_mode": "none",
                "resource": None,
                "resources": {
                    "diagram": runtime_state.get("diagram"),
                    "video": None,
                },
            },
        )
