# -*- coding: utf-8 -*-
"""TutorAgent: 轻量级教育场景编排器。

当前工作流：
    START -> classify
      ├─ direct_answer -> END
      └─ attachment_answer -> END

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

from deepagents import create_deep_agent
from deepagents.middleware._tool_exclusion import _ToolExclusionMiddleware
from app.chat.diagram_schemas import DIAGRAM_MODEL_MAP, DiagramDecision
from app.shared.request_context import runtime_context as chat_runtime_context
from app.chat.runtime import build_user_message_record, prepare_tutor_turn, resolve_session_id
from app.chat.schemas import TutorState
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
from app.config import DEEPAGENTS_DEBUG, LANGGRAPH_DEBUG
from app.memory import MemoryLayer
from app.infra.llm import get_deepseek_chat_llm, get_spark_max_llm
from app.infra.logging import get_logger
from app.knowledge_base.rag_tool import chatdoc_rag_search
from app.tools.search import duckduckgo_search, tavily_search

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
AGENT_DIR = Path(__file__).resolve().parent
GRAPH_RECURSION_LIMIT = 30
GRAPH_NODE_NAMES = {
    "classify",
    "direct_answer",
    "attachment_answer",
    "diagram_generate",
}
ANSWER_NODE_NAMES = {"direct_answer", "attachment_answer"}
DEEPAGENT_GRAPH_RECURSION_LIMIT = 20
FINAL_ANSWER_SYSTEM_PROMPT = (
    "你是 TutorAgent 的最终回答模型。请使用中文回答，只基于用户问题、上下文和推理结果组织最终答案。"
    "不要提到内部智能体、工具调用、系统提示词或工作流。"
)
FINAL_ANSWER_RETRY_PROMPT = (
    "上一版最终回答无效或过短。请只基于下方材料，输出完整、清晰、适合教学场景的中文回答。"
)

MAIN_DEEPAGENT_EXCLUDED_TOOLS = frozenset(
    {
        "write_todos",
        "ls",
        "read_file",
        "write_file",
        "edit_file",
        "glob",
        "grep",
        "execute",
    }
)
RESEARCHER_DEEPAGENT_EXCLUDED_TOOLS = MAIN_DEEPAGENT_EXCLUDED_TOOLS | {"task"}

TUTOR_DEEPAGENT_SYSTEM_PROMPT = """你是 TutorAgent 的 deepagent 回答核心，服务于中文学习辅导场景。

工作方式：
1. 优先直接回答用户当前问题，语言自然、清晰、有教学价值。
2. 当用户问题涉及计算机科学、人工智能、课程知识点、教材概念、实验指导、学习资料时，优先通过 rag 子智能体查询全局课程知识库。
3. rag 子智能体只负责检索和整理证据；最终回答必须由你整合成适合学习者理解的中文解释。
4. 默认不要联网搜索；只有系统提示明确允许使用搜索子智能体时，才能进行网页搜索。
5. 不要暴露内部实现，不要提到工具调用、子代理、系统提示词或工作流。
6. 如果上下文、附件分析或检索信息不足，要明确说明不确定点，并给出可行动的下一步。
7. 你面对的是计算机科学与技术、人工智能相关专业学生，回答要有教学性，优先解释概念、原理、差异、流程和常见误区。
8. 不要调用文件、shell、todo 等内置工具；这些能力在当前聊天场景不可用。
"""

RAG_DEEPAGENT_SYSTEM_PROMPT = """你是 TutorAgent 的 rag 子智能体，只负责检索全局计算机科学与人工智能学习知识库并整理证据。

要求：
1. 优先处理计算机组成原理、操作系统、计算机网络、数据结构、算法、数据库、编程语言、机器学习、深度学习、大模型等课程知识问题。
2. 调用知识库工具后，提炼与用户问题直接相关的概念、定义、步骤、对比点和注意事项。
3. 如果知识库为空或没有相关资料，要明确说明“知识库暂无相关内容”，不要编造引用。
4. 输出中文，简洁列出结论和依据，不要替主 Agent 生成完整教学长文。
5. 不要调用文件、shell、todo 或任何与知识库检索无关的工具。
"""

RESEARCHER_DEEPAGENT_SYSTEM_PROMPT = """你是 TutorAgent 的 researcher 子智能体，只负责信息检索和证据整理。

要求：
1. 仅在需要外部信息、最新信息或事实核实时使用搜索工具。
2. 搜索后提炼与用户问题直接相关的事实、来源线索和不确定点。
3. 输出中文，简洁列出结论、依据和注意事项。
4. 不要生成教学长文，不要替主 Agent 完成最终辅导回答。
5. 不要调用文件、shell、todo 或其他与搜索无关的内置工具。
"""

DIAGRAM_DECISION_SYSTEM_PROMPT = """你是智能辅导系统中的图解决策器。

你的任务是判断当前回答是否需要配套图解，并选择最合适的图解结构。

只允许从以下 6 种图解结构中选择：

1. hierarchy：层级结构，用于知识点组成、分类、结构拆解
2. flow：顺序流程，用于步骤、过程、运行机制
3. compare：对比结构，用于区别、优缺点、易混概念
4. relation：关系结构，用于依赖、因果、模块关系
5. sequence：交互时序，用于客户端/服务器、前后端、协议交互
6. state：状态变化，用于状态机、生命周期、算法过程

判断规则：
- 简单定义类问题，不需要图解
- 概念对比类问题，优先 compare
- 流程步骤类问题，优先 flow
- 组成结构类问题，优先 hierarchy
- 模块关系、因果依赖类问题，优先 relation
- 客户端/服务器、请求/响应、认证、握手类问题，优先 sequence
- 状态转换、生命周期、算法执行过程类问题，优先 state

如果用户显式要求图解，除非问题完全不适合图解，否则应尽量生成。
"""

DIAGRAM_GENERATION_SYSTEM_PROMPT = """你是智能辅导系统中的知识图解生成器。

你的任务是根据学生问题、最终文字回答和上下文，生成适合前端渲染的结构化图解对象。

重要要求：
- 你不能生成图片
- 你只能生成结构化图解数据
- 图解必须服务于教学理解
- 图解内容必须和最终回答一致
- 不要编造最终回答中不存在的关键事实
- title 不超过 20 个字
- summary 不超过 50 个字
- label 不超过 16 个字
- description 不超过 40 个字
- 节点数量控制在 3 到 8 个左右
- 输出 type 必须等于指定的 diagram_type
"""

# ---------------------------------------------------------------------------
# Prompt 加载
# ---------------------------------------------------------------------------
PROMPTS: dict[str, str] = load_prompts(AGENT_DIR)


def _build_tutor_system_prompt(*, enable_search: bool) -> str:
    if not enable_search:
        return (
            TUTOR_DEEPAGENT_SYSTEM_PROMPT
            + "\n搜索策略：本次请求前端没有开启搜索参数，主 Agent 不能使用搜索子智能体，也不要联网搜索。"
        )
    return (
        TUTOR_DEEPAGENT_SYSTEM_PROMPT
        + "\n搜索策略：本次请求前端已开启搜索参数，允许使用 researcher 子智能体进行网页搜索、最新信息核验和证据整理。"
    )


def _graph_stream_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "version": "v2",
        "config": {"recursion_limit": GRAPH_RECURSION_LIMIT},
    }
    if LANGGRAPH_DEBUG:
        kwargs["debug"] = True
    return kwargs


def _build_final_answer_prompt(
    *,
    state: TutorState,
    prompt_messages: list[Any],
    reasoning_answer: str,
    retry: bool = False,
) -> str:
    question = extract_question(prompt_messages)
    parts = []
    if retry:
        parts.append(FINAL_ANSWER_RETRY_PROMPT)
    parts.append(f"用户问题：{question or '未提取到明确问题'}")

    profile_context = str(state.get("profile_context", "")).strip()
    fact_context = str(state.get("fact_context", "")).strip()
    recent_chat_context = str(state.get("recent_chat_context", "")).strip()
    attachment_context = str(state.get("attachment_analysis_context", "")).strip()

    if profile_context:
        parts.append(f"用户画像上下文：\n{profile_context}")
    if fact_context:
        parts.append(f"长期记忆上下文：\n{fact_context}")
    if recent_chat_context:
        parts.append(f"近期对话上下文：\n{recent_chat_context}")
    if attachment_context:
        parts.append(f"附件预分析上下文：\n{attachment_context}")

    parts.append(f"DeepSeek 推理结果：\n{reasoning_answer}")
    parts.append("请输出最终答案，不要输出推理过程标题，不要暴露模型分工。")
    return "\n\n".join(parts)


class TutorAgent:
    """智能辅导 Agent — 轻量级编排器。

    两种对话路径：
    1. direct_answer — 纯文本对话，无需工具
    2. attachment_answer — 图片/文档分析后回答

    知识库检索与联网搜索由主 deepagent 自主委托子智能体完成，
    不再作为外层图节点参与路由。
    """

    _shared_instance: "TutorAgent | None" = None

    def __init__(self) -> None:
        # LLM 实例
        # 主模型使用 Spark Max，负责最终答案总结
        self.llm = get_spark_max_llm(temperature=0.7, streaming=True)
        # 研究模型使用 DeepSeek，负责思考过程和工具调用
        self.research_llm = get_deepseek_chat_llm(
            temperature=0.2,
            streaming=False,
            max_tokens=1200,
        )
        self.diagram_llm = get_deepseek_chat_llm(
            temperature=0.1,
            streaming=False,
            max_tokens=1600,
        )
        # 上下文服务
        self.memory_layer = MemoryLayer(module_name="mentor")

        # 图与工具
        self.graph = None
        self.deep_agent = None
        self._deep_agents: dict[bool, Any] = {}
        self._init_lock = asyncio.Lock()
        self._deep_agent_lock = asyncio.Lock()
        self._background_tasks: set[asyncio.Task] = set()

        logger.info("[TutorAgent] 初始化完成")

    @classmethod
    def get_shared(cls) -> "TutorAgent":
        """获取全局单例。"""
        if cls._shared_instance is None:
            cls._shared_instance = cls()
        return cls._shared_instance

    def _build_researcher_subagent(self) -> dict[str, Any]:
        """构建本地 researcher 子 deepagent。"""
        researcher_agent = create_deep_agent(
            model=self.research_llm,
            tools=[duckduckgo_search, tavily_search],
            subagents=[],
            system_prompt=RESEARCHER_DEEPAGENT_SYSTEM_PROMPT,
            middleware=[
                _ToolExclusionMiddleware(excluded=RESEARCHER_DEEPAGENT_EXCLUDED_TOOLS)
            ],
            debug=DEEPAGENTS_DEBUG,
        )

        return {
            "name": "researcher",
            "description": (
                "用于联网搜索、最新信息核验、资料检索和证据整理的研究子智能体。"
                "当用户问题涉及最新、最近、新闻、价格、外部资料或需要事实核实时使用。"
            ),
            "runnable": researcher_agent,
        }

    def _build_rag_subagent(self) -> dict[str, Any]:
        """构建本地 rag 子 deepagent。"""
        rag_agent = create_deep_agent(
            model=self.research_llm,
            tools=[chatdoc_rag_search],
            subagents=[],
            system_prompt=RAG_DEEPAGENT_SYSTEM_PROMPT,
            middleware=[
                _ToolExclusionMiddleware(excluded=RESEARCHER_DEEPAGENT_EXCLUDED_TOOLS)
            ],
            debug=DEEPAGENTS_DEBUG,
        )

        return {
            "name": "rag",
            "description": (
                "用于检索全局计算机科学与人工智能课程知识库的子智能体。"
                "当用户询问课程概念、教材知识点、实验指导、学习资料时优先使用。"
            ),
            "runnable": rag_agent,
        }

    def _build_deep_agent(self, *, enable_search: bool = False) -> Any:
        """构建 Tutor 主 deepagent，并把知识库检索/联网搜索隔离到本地子智能体。"""
        rag_subagent = self._build_rag_subagent()
        subagents = [rag_subagent]
        if enable_search:
            subagents.append(self._build_researcher_subagent())

        return create_deep_agent(
            model=self.research_llm,
            tools=[],
            subagents=subagents,
            system_prompt=_build_tutor_system_prompt(enable_search=enable_search),
            middleware=[_ToolExclusionMiddleware(excluded=MAIN_DEEPAGENT_EXCLUDED_TOOLS)],
            debug=DEEPAGENTS_DEBUG,
        )

    async def _ensure_deep_agent(self, *, enable_search: bool = False) -> Any:
        """懒加载 deepagent，确保搜索子代理拿到最新工具实例。"""
        if enable_search in self._deep_agents:
            return self._deep_agents[enable_search]

        async with self._deep_agent_lock:
            if enable_search in self._deep_agents:
                return self._deep_agents[enable_search]
            built = self._build_deep_agent(enable_search=enable_search)
            self._deep_agents[enable_search] = built
            if not enable_search:
                self.deep_agent = built
            logger.info("[TutorAgent] deepagent 构建完成 enable_search=%s", enable_search)
            return built

    # ------------------------------------------------------------------
    # 图构建
    # ------------------------------------------------------------------
    async def _ensure_graph(self) -> None:
        """构建 LangGraph 状态图。"""
        if self.graph is not None:
            return

        async with self._init_lock:
            if self.graph is not None:
                return

            logger.info("[TutorAgent] 图构建开始")
            await self._ensure_deep_agent(enable_search=False)

            graph = StateGraph(TutorState)
            graph.add_node("classify", self._classify_node)
            graph.add_node("direct_answer", self._direct_answer_node)
            graph.add_node("attachment_answer", self._attachment_answer_node)
            graph.add_node("diagram_generate", self._diagram_generate_node)

            graph.add_edge(START, "classify")
            graph.add_conditional_edges(
                "classify",
                classify_route,
                {
                    "direct": "direct_answer",
                    "attachment_needed": "attachment_answer",
                },
            )
            graph.add_edge("direct_answer", "diagram_generate")
            graph.add_edge("attachment_answer", "diagram_generate")
            graph.add_edge("diagram_generate", END)

            self.graph = graph.compile()
            logger.info("[TutorAgent] 图构建完成")

    # ------------------------------------------------------------------
    # 节点: classify
    # ------------------------------------------------------------------
    async def _classify_node(self, state: TutorState) -> dict[str, Any]:
        """分类节点：仅区分 direct / attachment_needed。"""
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        messages = state.get("messages") or []
        file_urls = state.get("file_urls") or []
        image_urls = state.get("image_urls") or []
        resource_mode = state.get("resource_mode", "none")
        enable_search = bool(state.get("enable_search", False))
        user_message = extract_question(messages)

        with node_timer("classify", user=user_id, session=session_id):
            # 快速路径1：附件优先
            if file_urls or image_urls:
                logger.debug(
                    "[TutorAgent] 路由分类 route=attachment_needed reason=attachments_present images=%s files=%s resource_mode=%s",
                    len(image_urls),
                    len(file_urls),
                    resource_mode,
                )
                return {"route": "attachment_needed", "execution_mode": "attachment"}

            logger.debug(
                "[TutorAgent] 路由分类 route=direct reason=no_attachments resource_mode=%s question=%s",
                resource_mode,
                truncate(user_message, 120),
            )
            result = {"route": "direct", "execution_mode": "direct"}
            if enable_search:
                result["enable_search"] = True
            return result

    # ------------------------------------------------------------------
    # 回答执行公共方法
    # ------------------------------------------------------------------
    async def _run_answer_model(
        self,
        *,
        state: TutorState,
        stage_name: str,
        prompt_messages: list[Any],
        extra_log: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """统一执行回答模型，包含无效回复兜底。"""
        extra_log = extra_log or {}
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        system_prompt = state.get("system_prompt", "")
        enable_search = bool(state.get("enable_search", False))

        with node_timer(stage_name, user=user_id, session=session_id, **extra_log):
            full_messages = build_messages(system_prompt, prompt_messages)
            agent = await self._ensure_deep_agent(enable_search=enable_search)
            try:
                agent_result = await agent.ainvoke(
                    {"messages": full_messages},
                    config={
                        "recursion_limit": DEEPAGENT_GRAPH_RECURSION_LIMIT,
                        "configurable": {
                            "thread_id": f"tutor:{user_id}:{session_id}:{stage_name}",
                        },
                    },
                )
            except Exception:
                logger.exception("[TutorAgent] %s DeepSeek 推理阶段失败", stage_name)
                raise
            agent_messages = agent_result.get("messages", []) if isinstance(agent_result, dict) else []
            response = next(
                (msg for msg in reversed(agent_messages) if isinstance(msg, AIMessage)),
                None,
            )
            text = normalize_message_content(response.content if response else "")

            if is_unusable_reply_text(text):
                logger.warning("[TutorAgent] %s 重试 原因=无效回复", stage_name)
                retry_messages = (agent_messages or full_messages) + [
                    HumanMessage(
                        content="你上一条回复无效或过短。请重新回答用户问题，给出完整、可读、适合教学场景的中文回答。"
                    )
                ]
                retry_result = await agent.ainvoke(
                    {"messages": retry_messages},
                    config={
                        "recursion_limit": DEEPAGENT_GRAPH_RECURSION_LIMIT,
                        "configurable": {
                            "thread_id": f"tutor:{user_id}:{session_id}:{stage_name}:retry",
                        },
                    },
                )
                retry_messages_result = (
                    retry_result.get("messages", []) if isinstance(retry_result, dict) else []
                )
                retry_resp = next(
                    (msg for msg in reversed(retry_messages_result) if isinstance(msg, AIMessage)),
                    None,
                )
                retry_text = normalize_message_content(retry_resp.content if retry_resp else "")
                if not is_unusable_reply_text(retry_text):
                    response = retry_resp
                    text = retry_text

            reasoning_answer = text
            final_text = reasoning_answer
            try:
                final_text = await self._run_final_answer_llm(
                    state=state,
                    stage_name=stage_name,
                    prompt_messages=prompt_messages,
                    reasoning_answer=reasoning_answer,
                )
            except Exception as exc:
                logger.warning(
                    "[TutorAgent] %s Spark 最终回答失败，回退 DeepSeek 结果: %s",
                    stage_name,
                    exc,
                )

            if is_unusable_reply_text(final_text):
                final_text = reasoning_answer

            response = AIMessage(content=final_text)

            logger.debug("[TutorAgent] %s 完成 preview=%s", stage_name, truncate(final_text, 220))
            return {
                "messages": [response],
                "answer_text": final_text,
                "termination_reason": f"{stage_name}_done",
            }

    async def _run_final_answer_llm(
        self,
        *,
        state: TutorState,
        stage_name: str,
        prompt_messages: list[Any],
        reasoning_answer: str,
    ) -> str:
        """使用 Spark Max 生成最终回答；只传普通文本 SystemMessage + HumanMessage。"""
        for retry in (False, True):
            messages = [
                SystemMessage(content=FINAL_ANSWER_SYSTEM_PROMPT),
                HumanMessage(
                    content=_build_final_answer_prompt(
                        state=state,
                        prompt_messages=prompt_messages,
                        reasoning_answer=reasoning_answer,
                        retry=retry,
                    )
                ),
            ]
            logger.debug(
                "[TutorAgent] %s Spark 最终回答调用 retry=%s prompt=%s",
                stage_name,
                retry,
                truncate(messages[1].content, 260),
            )
            response = await self.llm.ainvoke(messages)
            text = normalize_message_content(getattr(response, "content", response))
            if not is_unusable_reply_text(text):
                return text
            logger.warning("[TutorAgent] %s Spark 最终回答无效 retry=%s", stage_name, retry)
        return reasoning_answer

    # ------------------------------------------------------------------
    # 节点: direct_answer
    # ------------------------------------------------------------------
    async def _direct_answer_node(self, state: TutorState) -> dict[str, Any]:
        """直接回答路径：纯文本对话，不调用工具。"""
        messages = state.get("messages") or []
        question = extract_question(messages)
        logger.debug("[TutorAgent] 直接回答 route=direct_answer question=%s", truncate(question, 180))

        return await self._run_answer_model(
            state=state,
            stage_name="direct_answer",
            prompt_messages=list(messages),
            extra_log={"route": "direct_answer"},
        )

    # ------------------------------------------------------------------
    # 节点: attachment_answer
    # ------------------------------------------------------------------
    async def _attachment_answer_node(self, state: TutorState) -> dict[str, Any]:
        """附件理解路径：消费上传阶段完成的图片/文档预分析后回答。"""
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        file_urls = state.get("file_urls") or []
        image_urls = state.get("image_urls") or []
        messages = list(state.get("messages") or [])
        question = extract_question(messages)
        pre_analysis = state.get("attachment_analysis") or {}

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

            full_context = str(state.get("attachment_analysis_context", "")).strip()
            if not full_context and isinstance(pre_analysis, dict):
                full_context = str(pre_analysis.get("analysis_context", "")).strip()

            if not full_context:
                full_context = (
                    "本轮包含附件，但上传阶段未返回可用的附件预分析结果。"
                    "请基于用户问题说明目前无法可靠读取附件内容，并建议用户重新上传或稍后重试。"
                )

            answer_prompt = (
                f"用户问题: {question}\n\n"
                f"以下是上传阶段已经完成的附件预分析内容：\n{full_context}\n\n"
                "请只根据这些预分析内容和已有对话回答用户问题，不要尝试读取附件、调用文件工具或重新分析图片。"
                "如果内容不足以回答问题，请明确说明缺失点；"
                "回答要清晰、分点、适合教学场景。"
            )

            result = await self._run_answer_model(
                state=state,
                stage_name="attachment_answer",
                prompt_messages=[HumanMessage(content=answer_prompt)],
                extra_log={"route": "attachment_answer"},
            )
            result["attachment_analysis_result"] = {
                "mode": "upload_preanalysis",
                "analysis_context": full_context,
            }
            return result

    async def _decide_diagram(
        self,
        *,
        question: str,
        answer: str,
        state: TutorState,
    ) -> DiagramDecision:
        """判断是否需要为最终回答补充结构化图解。"""
        requested = state.get("need_diagram")
        if requested is False:
            return DiagramDecision(
                need_diagram=False,
                diagram_type=None,
                reason="用户未开启图解生成",
            )

        prompt = (
            f"用户问题：\n{question}\n\n"
            f"最终回答：\n{answer}\n\n"
            f"用户是否主动要求图解：{bool(requested)}\n\n"
            "请判断是否需要生成图解，并选择最合适的 diagram_type。"
        )

        try:
            structured_llm = self.diagram_llm.with_structured_output(DiagramDecision)
            decision = await structured_llm.ainvoke(
                [
                    SystemMessage(content=DIAGRAM_DECISION_SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ]
            )
            decision = DiagramDecision.model_validate(decision)
            if decision.diagram_type not in DIAGRAM_MODEL_MAP:
                if not decision.need_diagram:
                    return decision
                return DiagramDecision(
                    need_diagram=False,
                    diagram_type=None,
                    reason="图解类型不受支持",
                )
            if requested is True and not decision.need_diagram:
                return DiagramDecision(
                    need_diagram=True,
                    diagram_type=decision.diagram_type,
                    reason=decision.reason,
                )
            if not decision.need_diagram:
                return decision
            return decision
        except Exception as exc:
            logger.warning("[TutorAgent] 图解决策失败: %s", exc)
            return DiagramDecision(
                need_diagram=False,
                diagram_type=None,
                reason="图解决策失败",
            )

    async def _generate_diagram_by_type(
        self,
        *,
        diagram_type: str,
        question: str,
        answer: str,
        state: TutorState,
    ) -> Optional[dict[str, Any]]:
        """按已决策的类型生成前端可渲染的结构化图解。"""
        model_cls = DIAGRAM_MODEL_MAP.get(diagram_type)
        if model_cls is None:
            return None

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
            "请严格生成指定 diagram_type 对应的结构化图解对象。"
        )

        try:
            structured_llm = self.diagram_llm.with_structured_output(model_cls)
            diagram = await structured_llm.ainvoke(
                [
                    SystemMessage(content=DIAGRAM_GENERATION_SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ]
            )
            validated = model_cls.model_validate(diagram)
            return validated.model_dump(by_alias=True)
        except Exception as exc:
            logger.warning("[TutorAgent] 图解生成失败 type=%s error=%s", diagram_type, exc)
            return None

    async def _diagram_generate_node(self, state: TutorState) -> TutorState:
        """回答后的可选图解生成节点；失败时降级为无图解。"""
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        with node_timer("diagram_generate", user=user_id, session=session_id):
            try:
                question = extract_question(state.get("messages") or [])
                answer = ""
                for key in ("final_answer", "answer_text", "answer", "response"):
                    value = state.get(key)  # type: ignore[literal-required]
                    if value:
                        answer = normalize_message_content(value)
                        break

                if not question or not answer:
                    state["diagram"] = None
                    state["diagram_error"] = "缺少问题或回答，跳过图解生成"
                    return state

                decision = await self._decide_diagram(
                    question=question,
                    answer=answer,
                    state=state,
                )
                if not decision.need_diagram or not decision.diagram_type:
                    state["diagram"] = None
                    return state

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
        """安全启动后台任务。"""
        task = asyncio.create_task(coro, name=task_name)
        self._background_tasks.add(task)

        def _done_callback(done_task: asyncio.Task) -> None:
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
        generate_image: bool = False,
        generate_video: bool = False,
        enable_search: bool = False,
        need_diagram: bool = False,
        resource_mode: Optional[str] = None,
        attachment_analysis: Optional[dict[str, Any]] = None,
    ):
        """流式生成对话响应。"""
        requested_image_urls = image_urls or []
        requested_file_urls = file_urls or []
        resource_requested = bool(resource_mode and resource_mode != "none") or generate_image or generate_video
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

        prepared_turn = await prepare_tutor_turn(
            ctx_service=self.memory_layer,
            prompts=PROMPTS,
            user_id=user_id,
            user_message=user_message,
            session_id=effective_session,
            image_urls=requested_image_urls,
            file_urls=requested_file_urls,
            enable_search=enable_search,
            need_diagram=need_diagram,
            attachment_analysis=attachment_analysis,
        )
        initial_state = prepared_turn.initial_state

        full_reply = ""
        runtime_state: dict[str, Any] = dict(initial_state)
        graph_error_text = ""
        active_node = ""

        try:
            with chat_runtime_context(user_id, effective_session):
                async for event in self.graph.astream_events(initial_state, **_graph_stream_kwargs()):
                    kind = event.get("event", "")
                    name = event.get("name", "")

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

                    if kind == "on_chain_end" and name in GRAPH_NODE_NAMES:
                        active_node = ""
                        node_output = event.get("data", {}).get("output", {})
                        if isinstance(node_output, dict):
                            for key, value in node_output.items():
                                if key == "messages" and isinstance(value, list):
                                    runtime_state[key] = list(runtime_state.get(key, [])) + value
                                else:
                                    runtime_state[key] = value

                    if kind == "on_chain_end" and name in ANSWER_NODE_NAMES:
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

        if graph_error_text:
            yield stream_event("error", graph_error_text)
            return

        if not full_reply:
            messages = runtime_state.get("messages", [])
            if isinstance(messages, list):
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage):
                        full_reply = normalize_message_content(msg.content)
                        break

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
            )

            self._spawn_background(
                self.memory_layer.post_turn_pipeline(
                    user_id=user_id,
                    session_id=effective_session,
                    user_message=user_message,
                    assistant_reply=full_reply,
                ),
                task_name="post_chat_pipeline",
            )
        except Exception as exc:
            logger.exception("[TutorAgent] 回复保存失败")
            yield stream_event("error", f"保存回复失败: {exc}")
            return

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
