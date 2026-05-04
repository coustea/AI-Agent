# -*- coding: utf-8 -*-
"""
AvatarAgent — 数字人独立 LangGraph 智能体

与 TutorAgent 对等但独立的 Agent：
- 独立的 LangGraph StateGraph 和 system prompt
- 复用 infra/llm 等共享基础设施
- 独立的记忆（source="avatar_fact"），共享画像
- 输出适配：口语化文本 + 工具事件
- 支持附件处理和图解生成
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated, Any, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, AnyMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from app.shared.diagram_render import build_mermaid_render
from app.chat.schemas import DIAGRAM_MODEL_MAP, DiagramDecision
from app.chat.utils import load_prompts, truncate
from app.infra.logging import get_logger
from app.infra.llm import get_llm_manager
from app.memory import MemoryLayer
from app.shared.json_utils import parse_first_json_object
from app.shared.image_analyze import build_vision_service
from app.tools.search import duckduckgo_search, tavily_search

logger = get_logger(__name__)

# 搜索工具列表
AVATAR_TOOLS = [duckduckgo_search, tavily_search]

# 搜索关键词（与 TutorAgent 分类逻辑一致）
SEARCH_KEYWORDS = (
    "搜索", "搜一下", "查一下", "查找", "检索", "帮我找", "网上", "近几年", "最新",
)

# Agent 所在目录
AGENT_DIR = Path(__file__).resolve().parent


class AvatarState(TypedDict, total=False):
    """AvatarAgent LangGraph 状态"""
    user_id: int
    session_id: str
    image_urls: Optional[list[str]]
    file_urls: Optional[list[str]]
    route: str  # "direct" | "tool_needed" | "vision_needed" | "attachment_needed"
    system_prompt: str
    tool_system_prompt: str
    messages: Annotated[list[AnyMessage], add_messages]
    input_source: str  # "asr" | "text"
    need_diagram: bool
    diagram: Optional[dict[str, Any]]
    diagram_error: Optional[str]
    attachment_analysis_context: str
    answer_text: str


# Make avatar and text agents share the same goal/prompt definition.
CHAT_AGENT_DIR = Path(__file__).resolve().parent.parent / "chat"
PROMPTS: dict[str, str] = load_prompts(CHAT_AGENT_DIR)


def _get_prompt(name: str) -> str:
    """获取提示词，如果不存在返回空字符串。"""
    return PROMPTS.get(name, "")


class AvatarAgent:
    """数字人 Agent — 独立 LangGraph 图

    工作流：
        START -> classify
          ├─ direct_answer (Spark 直接回答) -> diagram_generate -> END
          ├─ search_node (Spark 搜索) -> spark_summary -> diagram_generate -> END
          ├─ attachment_answer (Spark 基于附件回答) -> diagram_generate -> END
          └─ vision_answer (GLM 视觉) -> diagram_generate -> END
    """

    def __init__(self) -> None:
        self.llm_manager = get_llm_manager()
        self.spark_model_kwargs = {"temperature": 0.7, "streaming": True}
        self.classifier_model_kwargs = {"temperature": 0.0, "max_tokens": 100}
        self.tool_model_kwargs = {"temperature": 0.2, "streaming": False}
        self.diagram_model_kwargs = {"temperature": 0.1, "streaming": False, "max_tokens": 1600}
        self.memory_layer = MemoryLayer(module_name="avatar")
        self.vision_service = build_vision_service(self.llm_manager)
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 状态机"""
        graph = StateGraph(AvatarState)

        # 添加节点
        graph.add_node("classify", self._classify_node)
        graph.add_node("direct_answer", self._direct_answer_node)
        graph.add_node("vision_answer", self._vision_answer_node)
        graph.add_node("attachment_answer", self._attachment_answer_node)
        graph.add_node("search_node", self._search_node)
        graph.add_node("spark_summary", self._spark_summary_node)
        graph.add_node("diagram_generate", self._diagram_generate_node)

        # 边
        graph.set_entry_point("classify")
        graph.add_conditional_edges(
            "classify",
            self._route_after_classify,
            {
                "direct": "direct_answer",
                "vision_needed": "vision_answer",
                "attachment_needed": "attachment_answer",
                "search": "search_node",
            },
        )
        graph.add_edge("direct_answer", "diagram_generate")
        graph.add_edge("vision_answer", "diagram_generate")
        graph.add_edge("attachment_answer", "diagram_generate")
        graph.add_edge("search_node", "spark_summary")
        graph.add_edge("spark_summary", "diagram_generate")
        graph.add_edge("diagram_generate", END)

        return graph.compile()

    async def chat_stream(
        self,
        user_id: int,
        session_id: str,
        user_message: str | None = None,
        user_text: str | None = None,
        profile_ctx: str | None = None,
        memory_ctx: str | None = None,
        chat_ctx: list[AnyMessage] | None = None,
        input_source: str = "text",
        image_urls: list[str] | None = None,
        file_urls: list[str] | None = None,
        attachment_analysis: dict[str, Any] | None = None,
        need_diagram: bool = False,
        enable_search: bool = False,
    ):
        """流式生成 — yield 事件字典

        事件类型：
        - {"type": "text_chunk", "content": "..."}
        - {"type": "tool_result", "data": {...}}
        - {"type": "tool_error", "data": "..."}
        - {"type": "diagram", "data": {...}}
        - {"type": "complete", "full_response": "...", "diagram": {...}}
        """
        text = (user_message if user_message is not None else user_text) or ""
        image_urls = image_urls or []
        file_urls = file_urls or []
        attachment_analysis_context = str((attachment_analysis or {}).get("analysis_context", "")).strip()

        if chat_ctx is None:
            _, recent_chat_context = await self.memory_layer.build_recent_chat_context(
                user_id=user_id,
                session_id=session_id,
                user_message=text,
                image_urls=image_urls,
                file_urls=file_urls,
            )
            chat_ctx = []
        else:
            recent_chat_context = self._format_chat_ctx(chat_ctx)

        if profile_ctx is None or memory_ctx is None:
            built_profile_ctx, built_memory_ctx = await asyncio.gather(
                self.memory_layer.build_profile_context(user_id),
                self.memory_layer.build_long_term_memory_context(user_id),
            )
            profile_ctx = profile_ctx if profile_ctx is not None else built_profile_ctx
            memory_ctx = memory_ctx if memory_ctx is not None else built_memory_ctx

        # 构建系统提示词
        system_prompt = _get_prompt("direct_system").format(
            profile_context=profile_ctx or "暂无",
            fact_context=memory_ctx or "暂无",
            recent_chat_context=recent_chat_context,
        )
        tool_system_prompt = _get_prompt("tool_system").format(
            profile_context=profile_ctx or "暂无",
            fact_context=memory_ctx or "暂无",
            recent_chat_context=recent_chat_context,
            skills_context=self._build_skills_context(),
            file_info_context=self.memory_layer.build_file_context(image_urls, file_urls),
        )

        initial_state = AvatarState(
            user_id=user_id,
            session_id=session_id,
            image_urls=image_urls,
            file_urls=file_urls,
            input_source=input_source,
            route="",
            system_prompt=system_prompt,
            tool_system_prompt=tool_system_prompt,
            messages=[HumanMessage(content=text)],
            need_diagram=need_diagram,
            diagram=None,
            diagram_error=None,
            attachment_analysis_context=attachment_analysis_context,
            answer_text="",
        )

        full_response = ""
        diagram_data = None

        async for event in self._graph.astream_events(
            initial_state,
            version="v2",
            config={"recursion_limit": 15},
        ):
            kind = event.get("event", "")

            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    full_response += chunk.content
                    yield {"type": "text_chunk", "content": chunk.content}

            elif kind == "on_chain_end":
                name = event.get("name", "")
                if name in ("vision_answer", "direct_answer", "attachment_answer", "spark_summary"):
                    output = event.get("data", {}).get("output", {})
                    msgs = output.get("messages", []) if isinstance(output, dict) else []
                    if msgs:
                        last = msgs[-1]
                        if hasattr(last, "content") and last.content and not full_response:
                            full_response = last.content
                            yield {"type": "text_chunk", "content": last.content}
                elif name == "diagram_generate":
                    output = event.get("data", {}).get("output", {})
                    if isinstance(output, dict):
                        diagram_data = output.get("diagram")
                        if diagram_data:
                            yield {"type": "diagram", "data": diagram_data}

            elif kind == "on_tool_end":
                tool_output = event.get("data", {}).get("output", "")
                tool_name = ""
                tags = event.get("tags", [])
                for tag in tags:
                    if tag.startswith("langchain_tool:"):
                        tool_name = tag.split(":")[-1]
                        break
                yield {
                    "type": "tool_result",
                    "data": {
                        "tool_name": tool_name,
                        "result": str(tool_output) if tool_output else "",
                    },
                }

            elif kind == "on_tool_error":
                yield {
                    "type": "tool_error",
                    "data": str(event.get("data", {}).get("error", "工具调用失败")),
                }

        yield {"type": "complete", "full_response": full_response, "diagram": diagram_data}

    # ---- 节点方法 ----

    async def _classify_node(self, state: AvatarState) -> dict:
        """分类节点：direct / search / vision_needed / attachment_needed"""
        messages = state.get("messages", [])
        user_msg = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                user_msg = m.content
                break

        file_urls = state.get("file_urls") or []
        image_urls = state.get("image_urls") or []
        enable_search = state.get("enable_search", False)

        # 路径1：有文件附件 → attachment_answer
        if file_urls:
            logger.debug("[AvatarAgent] 路由 route=attachment_needed reason=file_attachments")
            return {"route": "attachment_needed"}

        # 路径2：需要搜索
        if enable_search or any(kw in user_msg for kw in SEARCH_KEYWORDS):
            logger.debug("[AvatarAgent] 路由 route=search reason=enable_search_or_keywords")
            return {"route": "search"}

        # 路径3：仅图片 → vision_answer
        if image_urls:
            logger.debug("[AvatarAgent] 路由 route=vision_needed reason=image_attachments")
            return {"route": "vision_needed"}

        # 路径4：ASR 短句倾向直接回答
        if state.get("input_source") == "asr" and len(user_msg) < 20:
            return {"route": "direct"}

        # LLM 分类
        try:
            classifier_prompt = _get_prompt("classifier")
            result = await self.llm_manager.ainvoke(
                "spark_max",
                classifier_prompt.format(
                    user_message=user_msg,
                    has_attachments="是" if (file_urls or image_urls) else "否",
                ),
                model_kwargs=self.classifier_model_kwargs,
            )
            route = result.content.strip().strip('"').strip("'")
            if route not in ("direct", "tool_needed", "vision_needed", "attachment_needed"):
                route = "direct"
        except Exception:
            route = "direct"

        return {"route": route}

    def _route_after_classify(self, state: AvatarState) -> str:
        route = state.get("route", "direct")
        if route == "vision_needed":
            return "vision_needed"
        elif route == "attachment_needed":
            return "attachment_needed"
        elif route == "search":
            return "search"
        return "direct"

    async def _direct_answer_node(self, state: AvatarState) -> dict:
        """直接回答路径"""
        messages = [SystemMessage(content=state["system_prompt"])] + state["messages"]
        response = await self.llm_manager.ainvoke(
            "spark_max",
            messages,
            model_kwargs=self.spark_model_kwargs,
        )
        text = getattr(response, "content", "")
        return {"messages": [response], "answer_text": text}

    async def _vision_answer_node(self, state: AvatarState) -> dict:
        """视觉回答路径 — 使用 GLM 多模态"""
        messages = state.get("messages") or []
        user_msg = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                user_msg = m.content
                break
        result = await self.vision_service.analyze_images(state.get("image_urls") or [], user_msg)
        text = str(result.get("analysis_text", "")).strip() or "我看完图片了，我们继续。"
        return {"messages": [AIMessage(content=text)], "answer_text": text}

    async def _attachment_answer_node(self, state: AvatarState) -> dict:
        """附件回答路径 — 基于附件预分析结果回答"""
        messages = state.get("messages") or []
        user_msg = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                user_msg = m.content
                break

        # 获取附件分析上下文
        full_context = state.get("attachment_analysis_context", "")
        if not full_context:
            full_context = (
                "本轮包含附件，但上传阶段未返回可用的附件预分析结果。"
                "请基于用户问题说明目前无法可靠读取附件内容，并建议用户重新上传或稍后重试。"
            )

        answer_prompt = (
            f"用户问题: {user_msg}\n\n"
            f"以下是上传阶段已经完成的附件预分析内容：\n{full_context}\n\n"
            "请根据这些预分析内容回答用户问题。"
            "回答要口语化、简短、适合语音播报。"
        )

        full_messages = [SystemMessage(content=state["system_prompt"]), HumanMessage(content=answer_prompt)]
        response = await self.llm_manager.ainvoke(
            "spark_max",
            full_messages,
            model_kwargs=self.spark_model_kwargs,
        )
        text = getattr(response, "content", "")
        return {"messages": [response], "answer_text": text}

    async def _search_node(self, state: AvatarState) -> dict:
        """搜索节点：Spark 使用搜索工具查找信息"""
        messages = state.get("messages") or []
        user_msg = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                user_msg = m.content
                break

        logger.info("[AvatarAgent] 搜索节点 question=%s", truncate(user_msg, 180))

        full_messages = [SystemMessage(content=state["tool_system_prompt"])] + list(messages)

        # 绑定搜索工具
        llm_with_tools = self.llm_manager.bind_tools(
            "spark_max",
            AVATAR_TOOLS,
            model_kwargs=self.tool_model_kwargs,
        )

        response = await self.llm_manager.ainvoke_runnable(
            llm_with_tools,
            full_messages,
            model_type="spark_max",
        )

        # 处理工具调用
        search_result = getattr(response, "content", "")
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
                    else:
                        result = ""
                    tool_results.append(f"【{tool_name}】\n{result}")
                except Exception as exc:
                    logger.warning("[AvatarAgent] 搜索工具 %s 失败: %s", tool_name, exc)
                    tool_results.append(f"【{tool_name}】搜索失败")

            search_result = search_result + "\n\n" + "\n\n".join(tool_results)

        return {"search_result": search_result}

    async def _spark_summary_node(self, state: AvatarState) -> dict:
        """Spark 总结节点：基于搜索结果生成教学回答"""
        messages = state.get("messages") or []
        search_result = state.get("search_result", "")
        user_msg = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                user_msg = m.content
                break

        prompt = (
            f"用户问题：{user_msg}\n\n"
            f"搜索结果：\n{search_result}\n\n"
            "请基于搜索结果回答用户问题，语言自然、口语化、适合语音播报。"
        )

        full_messages = [
            SystemMessage(content=state["system_prompt"]),
            HumanMessage(content=prompt),
        ]

        response = await self.llm_manager.ainvoke(
            "spark_max",
            full_messages,
            model_kwargs=self.spark_model_kwargs,
        )
        text = getattr(response, "content", "")
        return {"messages": [response], "answer_text": text}

    async def _diagram_generate_node(self, state: AvatarState) -> dict:
        """图解生成节点"""
        need_diagram = state.get("need_diagram", False)
        if not need_diagram:
            return {"diagram": None}

        messages = state.get("messages") or []
        question = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                question = m.content
                break

        answer = state.get("answer_text", "")
        if not answer:
            for m in reversed(messages):
                if isinstance(m, AIMessage):
                    answer = m.content
                    break

        if not question or not answer:
            return {"diagram": None, "diagram_error": "缺少问题或回答"}

        try:
            # 决策是否需要图解
            decision = await self._decide_diagram(question=question, answer=answer, state=state)
            if not decision.need_diagram or not decision.diagram_type:
                return {"diagram": None}

            # 生成图解
            diagram = await self._generate_diagram_by_type(
                diagram_type=decision.diagram_type,
                question=question,
                answer=answer,
                state=state,
            )
            return {"diagram": diagram}
        except Exception as exc:
            logger.warning("[AvatarAgent] 图解生成失败: %s", exc)
            return {"diagram": None, "diagram_error": str(exc)}

    async def _decide_diagram(self, question: str, answer: str, state: AvatarState) -> DiagramDecision:
        """判断是否需要生成图解"""
        prompt = (
            f"用户问题：\n{question}\n\n"
            f"最终回答：\n{answer}\n\n"
            "请判断是否需要生成图解，并选择最合适的 diagram_type。"
        )

        try:
            decision = await self.llm_manager.ainvoke_structured(
                "spark_max",
                DiagramDecision,
                [
                    SystemMessage(content=_get_prompt("diagram_decision_system")),
                    HumanMessage(content=prompt),
                ],
                strict=True,
                model_kwargs=self.diagram_model_kwargs,
            )

            if decision.diagram_type not in DIAGRAM_MODEL_MAP:
                return DiagramDecision(need_diagram=False, diagram_type=None, reason="图解类型不受支持")

            return decision
        except Exception as exc:
            logger.warning("[AvatarAgent] 图解决策失败: %s", exc)
            return DiagramDecision(need_diagram=False, diagram_type=None, reason="图解决策失败")

    async def _generate_diagram_by_type(
        self,
        diagram_type: str,
        question: str,
        answer: str,
        state: AvatarState,
    ) -> Optional[dict[str, Any]]:
        """按类型生成图解"""
        model_cls = DIAGRAM_MODEL_MAP.get(diagram_type)
        if model_cls is None:
            return None

        prompt = (
            f"diagram_type：{diagram_type}\n\n"
            f"学生问题：\n{question}\n\n"
            f"最终文字回答：\n{answer}\n\n"
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
            content = response.content if hasattr(response, "content") else str(response)
            return {
                "type": diagram_type,
                "title": f"{diagram_type} 图解",
                "summary": "Mermaid 知识图解",
                "render": build_mermaid_render(content),
            }
        except Exception as exc:
            logger.warning("[AvatarAgent] 图解生成失败 type=%s error=%s", diagram_type, exc)
            return None

    # ---- 辅助方法 ----

    @staticmethod
    def _format_chat_ctx(chat_ctx: list) -> str:
        if not chat_ctx:
            return "（无历史对话）"
        lines = []
        for msg in chat_ctx[-10:]:
            role = "学生" if isinstance(msg, HumanMessage) else "教师"
            lines.append(f"{role}: {msg.content}")
        return "\n".join(lines)

    @staticmethod
    def _build_skills_context() -> str:
        """返回可用工具列表。"""
        return "可用工具：duckduckgo_search, tavily_search"
