# -*- coding: utf-8 -*-
"""TutorAgent：基于上下文初始化的智能辅导编排器。

回答路由会流式输出文字讲解，然后可能生成 InsightCanvas 图板。
独立的图解请求则直接将上一轮对话可视化。"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any

from app.chat.request import ChatHistoryMessage
from app.chat.schemas import InsightCanvas, TutorAgentContext, TutorState
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
    build_messages,
)
from app.config import LANGGRAPH_DEBUG
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.prompts import registry
from app.chat.tools.search import duckduckgo_search, serp_search, tavily_search

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
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
    "direct_answer",
    "search_node",
    "spark_summary",
    "attachment_answer",
    "teaching_diagram_generate",
}
# 回答节点名称集合（会发送 token 事件）
ANSWER_NODE_NAMES = {"direct_answer", "spark_summary", "attachment_answer"}


def _get_prompt(name: str) -> str:
    """获取聊天模块的 prompt 文本。"""
    return registry.get(f"chat/{name}")


def _explicit_diagram_requested(user_message: str) -> bool:
    """仅在用户本轮显式请求时才激活图解图板。"""
    normalized = re.sub(r"\s+", "", (user_message or "").lower())
    if not normalized:
        return False
    if re.search(r"(?:不要|不需要|无需|别|取消|关闭).{0,8}(?:图解|画图|流程图|示意图|结构图|可视化)", normalized):
        return False
    patterns = (
        r"图解(?:说明|解释|展示|一下)?",
        r"(?:请|帮我|能否|可以)?(?:用|通过)(?:一张|一个)?(?:图|图解|图示)(?:说明|解释|展示|梳理|讲解)?",
        r"(?:请|帮我|能否|可以)?(?:用图|画图|画一下)(?:说明|解释|展示|梳理|讲解)?",
        r"(?:画|生成|提供|做|来)(?:一张|一个)?(?:流程图|示意图|结构图|时序图|图解|图示)",
        r"(?:把|将).{1,24}(?:画|整理|转成|做成)(?:一张|一个)?(?:图|图解|流程图|示意图)",
        r"(?:图示|视觉化)(?:说明|解释|展示|呈现|讲解)?",
        r"(?:可视化)(?:说明|解释|展示|呈现)",
        r"(?:diagram|visuali[sz]e|visualization)",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


def _diagram_only_requested(user_message: str) -> bool:
    """检测依赖上一轮教学回答的纯图解指令。"""
    normalized = re.sub(r"[\s，。！？!?、：:；;]", "", (user_message or "").lower())
    if not normalized:
        return False
    patterns = (
        r"(?:我想|我要|请|帮我|给我|能否|可以|麻烦)?(?:生成|制作|做|画|展示|提供|来)?(?:一张|一个)?(?:教学)?图解(?:说明)?(?:一下|看看)?",
        r"(?:我想|我要|请|帮我|给我|能否|可以|麻烦)?(?:生成|制作|做|画|展示|提供|来)?(?:一张|一个)?(?:流程图|示意图|结构图|时序图)(?:一下|看看)?",
    )
    return any(re.fullmatch(pattern, normalized) for pattern in patterns)


def _previous_teaching_exchange(messages: list[Any]) -> tuple[str, str]:
    """返回本轮之前的用户问题和助教讲解。"""
    latest_user_index = next(
        (index for index in range(len(messages) - 1, -1, -1) if isinstance(messages[index], HumanMessage)),
        -1,
    )
    if latest_user_index <= 0:
        return "", ""

    for answer_index in range(latest_user_index - 1, -1, -1):
        message = messages[answer_index]
        if not isinstance(message, AIMessage):
            continue
        answer = normalize_message_content(message.content).strip()
        if not answer:
            continue
        prior_question = extract_question(messages[:answer_index])
        if _diagram_only_requested(prior_question):
            # 连续的"生成图解"轮次必须继续使用最近的实质性讲解，
            # 而非更早的图解确认回复。
            continue
        return prior_question, answer
    return "", ""


def _search_requested(user_message: str) -> bool:
    """仅将明确的最新信息请求路由到联网搜索。"""
    normalized = re.sub(r"\s+", "", (user_message or "").lower())
    if not normalized:
        return False
    patterns = (
        r"(?:联网|上网)(?:搜索|查询|检索|查)",
        r"(?:搜索|检索|查一下|帮我查|查询)(?:一下)?(?:最新|今天|近期|当前|版本|新闻|资料)?",
        r"(?:最新|今天|今日|近期发布|最近更新|当前版本|实时|新闻)",
        r"(?:报错|异常堆栈|traceback|error|版本兼容|升级到|release)",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


def _answer_generation_policy(user_message: str) -> str:
    """选择提示词级别的回答深度，不施加输出截断。"""
    normalized = re.sub(r"\s+", "", (user_message or "").lower())
    is_learning_statement = bool(
        re.search(r"(?:我)?(?:最近|目前|现在|正在)?(?:在)?(?:学习|复习|了解|看)(?:一下)?", normalized)
    )
    asks_for_explanation = bool(
        re.search(r"(?:什么|为何|为什么|怎么|如何|解释|讲解|介绍|梳理|区别|对比|举例|详细|展开|请问|？|\?)", normalized)
    )
    if is_learning_statement and not asks_for_explanation:
        return (
            "本轮学生只是在陈述学习方向，尚未提出具体问题。"
            "请用简短回应确认主题价值，列出至多 3 个可继续提问的切入点，并邀请学生选择；"
            "不要直接展开完整课程讲义。"
        )
    if re.search(r"(?:详细|系统|深入|展开|完整|从头|全面|结合例题|结合代码)", normalized):
        return "学生明确需要深入讲解；在紧扣问题的前提下分层展开，并避免无关扩写。"
    return (
        "本轮采用默认答复深度：先直接回答核心问题，再用必要的要点或一个例子说明；"
        "若学生未要求深入，不要扩写成完整课程章节。"
    )


def _learner_context_requests(user_message: str) -> tuple[bool, bool]:
    """仅在问题需要个性化时选择读取学习者上下文。"""
    normalized = re.sub(r"\s+", "", (user_message or "").lower())
    if not normalized:
        return False, False

    profile_patterns = (
        r"(?:按|根据|结合).{0,8}(?:我的|本人)",
        r"我的(?:基础|水平|专业|目标|偏好|情况|学习风格|薄弱点|弱点)",
        r"(?:适合我|为我定制|给我定制|个性化)",
    )
    memory_patterns = (
        r"(?:我之前|我上次|之前我|以前我|我最近).{0,24}(?:学|不会|不懂|错误|做错|问题|薄弱|掌握)",
        r"我的(?:薄弱点|弱点|错题|学习记录|学习历史|历史问题)",
        r"(?:学到哪|记得我|回顾我|根据我.{0,8}(?:记录|历史))",
    )
    return (
        any(re.search(pattern, normalized) for pattern in profile_patterns),
        any(re.search(pattern, normalized) for pattern in memory_patterns),
    )


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

    四种对话路径：
    1. direct_answer — Spark MAX 直接回答，个性化请求可读取只读学习依据
    2. teaching_diagram_generate — 纯图解指令直接复用上一轮教学答案生成图板
    3. search_node → spark_summary — Spark MAX 搜索后 Spark MAX 总结
    4. attachment_answer — Spark MAX 基于附件分析结果回答
    """

    def __init__(self, context: TutorAgentContext) -> None:
        """初始化 TutorAgent。

        创建 LLM 实例、保存服务层构造好的上下文、初始化图。
        """
        self.context = context
        # LLM 实例
        self.llm = get_llm()

        # 图仅编排本轮对话；持久化上下文由服务层注入。
        self.graph = None
        self._init_lock = asyncio.Lock()

        logger.info("[TutorAgent] 初始化完成")

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------

    async def _stream_answer_with_retry(
        self,
        messages: list[Any],
        *,
        node_name: str,
        config: RunnableConfig,
        fallback_text: str = "抱歉，我暂时无法回答这个问题，请稍后重试。",
        retry_prompt: str = "请重新回答用户问题，给出完整、可读、适合教学场景的中文回答。",
    ) -> AIMessage:
        """流式输出文本块；仅在尚未输出可见内容时重试。"""
        has_visible_output = False

        async def generate(input_messages: list[Any]) -> AIMessage | None:
            nonlocal has_visible_output
            final_chunk = None
            try:
                async for chunk in self.llm.astream(
                    input_messages,
                    temperature=0.3,
                ):
                    if final_chunk is None:
                        final_chunk = chunk
                    else:
                        final_chunk += chunk
                        
                    text = _stream_chunk_text(chunk)
                    if text:
                        has_visible_output = True
                        await adispatch_custom_event(
                            "answer_token",
                            {"node": node_name, "text": text},
                            config=config,
                        )
                return final_chunk
            except Exception as exc:
                logger.warning("[TutorAgent] %s 流式调用失败 err=%s", node_name, exc)
                if has_visible_output:
                    raise
            return None

        result = await generate(messages)
        if result and (result.content or getattr(result, "tool_calls", [])):
            return result

        logger.warning("[TutorAgent] %s 重试 原因=未产生可见流式内容", node_name)
        result = await generate(messages + [HumanMessage(content=retry_prompt)])
        if result and (result.content or getattr(result, "tool_calls", [])):
            return result

        await adispatch_custom_event(
            "answer_token",
            {"node": node_name, "text": fallback_text},
            config=config,
        )
        return AIMessage(content=fallback_text)

    async def _load_learner_context(
        self,
        state: TutorState,
        config: RunnableConfig,
    ) -> tuple[str, str]:
        """仅在必要时通过注入的能力读取学习者依据。"""
        profile_context = str(state.get("retrieved_profile_context", "")).strip()
        memory_context = str(state.get("retrieved_memory_context", "")).strip()
        reader = self.context.learner_context_reader
        if reader is None:
            return profile_context, memory_context

        question = extract_question(state.get("messages") or [])
        need_profile, need_memory = _learner_context_requests(question)

        if need_profile and not profile_context:
            await adispatch_custom_event(
                "learner_context_status",
                {"stage": "reading_profile", "message": "正在读取学习画像以调整讲解方式..."},
                config=config,
            )
            try:
                profile_context = (await reader.read_learning_profile()).strip()
            except Exception as exc:
                logger.warning("[TutorAgent] 读取学习画像失败，继续通用回答 err=%s", exc)

        if need_memory and not memory_context:
            await adispatch_custom_event(
                "learner_context_status",
                {"stage": "searching_learning_memory", "message": "正在检索相关学习记录..."},
                config=config,
            )
            try:
                memory_context = (await reader.search_learning_memory(question)).strip()
            except Exception as exc:
                logger.warning("[TutorAgent] 检索学习记忆失败，继续通用回答 err=%s", exc)

        return profile_context, memory_context

    @staticmethod
    def _scoped_answer_prompt(
        system_prompt: str,
        *,
        question: str,
        profile_context: str,
        memory_context: str,
        diagram_enabled: bool,
    ) -> str:
        """基于本轮实际读取的依据组织回答提示词。"""
        sections = [
            system_prompt,
            f"# 本轮答复深度\n{_answer_generation_policy(question)}",
        ]
        evidence: list[str] = []
        if profile_context:
            evidence.append(f"## 按需读取的学习画像\n{profile_context}")
        if memory_context:
            evidence.append(f"## 按需检索的长期学习依据\n{memory_context}")
        if evidence:
            sections.append(
                "# 本轮按需读取的学习依据\n"
                "仅据下列真实记录调整回答，不要延伸推断学生能力或学习经历。\n\n"
                + "\n\n".join(evidence)
            )
        if diagram_enabled:
            sections.append(
                "# 本轮图解输出已启用\n"
                "系统会在文字回答之后生成并渲染结构化教学图板。"
                "正文只需要清楚回答问题；如果需要提及图解，只能说图板将随本轮回答展示。"
                "严禁声称无法生成可视化图解，严禁建议学生改用第三方绘图工具完成本轮请求。"
            )
        return "\n\n".join(sections)

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
            graph.add_node("teaching_diagram_generate", self._teaching_diagram_generate_node)

            # 添加边
            graph.add_edge(START, "classify")
            graph.add_conditional_edges(
                "classify",
                classify_route,
                {
                    "direct": "direct_answer",
                    "diagram_only": "teaching_diagram_generate",
                    "search": "search_node",
                    "attachment_needed": "attachment_answer",
                },
            )
            graph.add_conditional_edges(
                "direct_answer",
                self._route_after_answer,
                {
                    "diagram": "teaching_diagram_generate",
                    "end": END,
                },
            )
            graph.add_edge("search_node", "spark_summary")
            graph.add_conditional_edges(
                "spark_summary",
                self._route_after_answer,
                {
                    "diagram": "teaching_diagram_generate",
                    "end": END,
                },
            )
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
        """在文字回答完成后运行可选的每轮图解。"""
        return "diagram" if state.get("need_teaching_diagram", False) else "end"

    # ------------------------------------------------------------------
    # 节点: classify
    # ------------------------------------------------------------------

    async def _classify_node(self, state: TutorState) -> dict[str, Any]:
        """分类节点：根据用户意图和显式请求决定路由。

        路由规则：
        - 图解必须用户显式请求（前端按钮或文字明确要求）
        - 附件或搜索仅改变回答路径，回答完成后再按需生成图解
        """
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        messages = state.get("messages") or []
        attachments = state.get("attachments") or []
        enable_search = bool(state.get("enable_search", False))
        need_teaching_diagram = bool(state.get("need_teaching_diagram", False))
        user_message = extract_question(messages)

        has_attachments = bool(attachments)

        with node_timer("classify", user=user_id, session=session_id):
            enable_search = enable_search or _search_requested(user_message)

            # 图解不能由概率分类结果擅自开启，只接受 UI 开关或本轮显式文字请求。
            need_diagram = need_teaching_diagram or _explicit_diagram_requested(user_message)

            # 构造 state_updates
            state_updates: dict[str, Any] = {}
            if need_diagram != need_teaching_diagram:
                state_updates["need_teaching_diagram"] = need_diagram

            if enable_search:
                route = "search"
                execution_mode = "attachment_search" if has_attachments else "search"
            elif has_attachments:
                route = "attachment_needed"
                execution_mode = "attachment"
            elif need_diagram and _diagram_only_requested(user_message):
                _, prior_answer = _previous_teaching_exchange(list(messages))
                if prior_answer:
                    route = "diagram_only"
                    execution_mode = "diagram_only"
                else:
                    # 没有更早的讲解就没有可可视化的主题；
                    # 让正常回答路径去询问缺失的学习主题。
                    need_diagram = False
                    route = "direct"
                    execution_mode = "direct"
                    state_updates["need_teaching_diagram"] = False
            else:
                route = "direct"
                execution_mode = "direct"

            logger.debug(
                "[TutorAgent] 路由分类 route=%s execution_mode=%s need_diagram=%s question=%s",
                route,
                execution_mode,
                need_diagram,
                truncate(user_message, 120),
            )

            state_updates.update({
                "route": route,
                "execution_mode": execution_mode,
            })
            if enable_search != bool(state.get("enable_search", False)):
                state_updates["enable_search"] = True

            return state_updates

    # ------------------------------------------------------------------
    # 节点: direct_answer
    # ------------------------------------------------------------------

    async def _direct_answer_node(
        self,
        state: TutorState,
        config: RunnableConfig,
    ) -> dict[str, Any]:
        """直接回答路径：Spark MAX 直接回答，按需读取只读学习依据。

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

            profile_context, memory_context = await self._load_learner_context(state, config)
            scoped_prompt = self._scoped_answer_prompt(
                system_prompt,
                question=question,
                profile_context=profile_context,
                memory_context=memory_context,
                diagram_enabled=bool(state.get("need_teaching_diagram", False)),
            )
            full_messages = build_messages(scoped_prompt, list(messages))
            result = await self._stream_answer_with_retry(
                full_messages,
                node_name="direct_answer",
                config=config,
            )

            return {
                "messages": [result],
                "answer_text": result.content,
                "retrieved_profile_context": profile_context,
                "retrieved_memory_context": memory_context,
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
            llm_with_tools = self.llm.model.bind_tools(
                [duckduckgo_search, tavily_search, serp_search],
            )

            response = None
            try:
                response = await self.llm.ainvoke(full_messages, model=llm_with_tools)
            except Exception as exc:
                logger.warning("[TutorAgent] 搜索意图生成失败，进入直接检索兜底 err=%s", exc)

            # 处理工具调用
            search_result = normalize_message_content(getattr(response, "content", "") if response else "")

            # 如果有工具调用，执行它们
            tool_calls = getattr(response, "tool_calls", []) if response else []
            tool_results = []
            if tool_calls:
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
                        if result:
                            tool_results.append(f"【{tool_name}】\n{result}")
                    except Exception as exc:
                        logger.warning("[TutorAgent] 搜索工具 %s 失败: %s", tool_name, exc)
                        tool_results.append(f"【{tool_name}】搜索失败")

            # 兜底机制：如果模型没有生成工具调用，或者工具调用均无有效返回，则主动执行核心搜索兜底
            if not tool_results:
                logger.info("[TutorAgent] 搜索节点未触发工具调用或无结果，启动自动兜底搜索")
                # 优先使用 tavily_search
                tavily_result = ""
                try:
                    tavily_result = await tavily_search.ainvoke({"query": question})
                except Exception as exc:
                    logger.warning("[TutorAgent] 自动兜底 Tavily 搜索失败: %s", exc)

                # 如果 tavily_search 不可用或失败，则 fallback 到 duckduckgo_search
                if not tavily_result or "Tavily 搜索不可用" in tavily_result or "Tavily 搜索失败" in tavily_result:
                    logger.info("[TutorAgent] Tavily 不可用或失败，使用 DuckDuckGo 搜索兜底")
                    try:
                        ddg_result = await duckduckgo_search.ainvoke({"query": question})
                        if ddg_result and "DuckDuckGo 搜索失败" not in ddg_result:
                            tool_results.append(f"【duckduckgo_search (自动兜底)】\n{ddg_result}")
                        else:
                            tool_results.append("【自动搜索兜底】无可用搜索结果。")
                    except Exception as exc:
                        logger.warning("[TutorAgent] 自动兜底 DuckDuckGo 搜索失败: %s", exc)
                        tool_results.append("【自动搜索兜底】所有搜索引擎调用均失败。")
                else:
                    tool_results.append(f"【tavily_search (自动兜底)】\n{tavily_result}")

            # 合并搜索结果
            search_result = search_result + "\n\n" + "\n\n".join(tool_results)

            logger.debug("[TutorAgent] search_node 完成 preview=%s", truncate(search_result, 220))

            return {
                "search_result": search_result,
                "termination_reason": "search_done",
            }


    # ------------------------------------------------------------------
    # 节点: spark_summary
    # ------------------------------------------------------------------

    async def _spark_summary_node(
        self,
        state: TutorState,
        config: RunnableConfig,
    ) -> dict[str, Any]:
        """Spark 总结节点：基于搜索资料生成完整教学回答。"""
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
                f"参考资料：\n{search_result}\n\n"
                "请结合参考资料完整回答用户问题。语言自然、清晰、有教学价值。"
                "不要在回答中提及检索过程或内部工作流。"
            )
            fallback_text = search_result or "抱歉，我暂时无法回答这个问题，请稍后重试。"
            retry_prompt = "请基于已有资料重新回答，给出完整、可读、适合教学场景的中文回答。"
            profile_context, memory_context = await self._load_learner_context(state, config)
            scoped_prompt = self._scoped_answer_prompt(
                system_prompt,
                question=question,
                profile_context=profile_context,
                memory_context=memory_context,
                diagram_enabled=bool(state.get("need_teaching_diagram", False)),
            )

            full_messages = [
                SystemMessage(content=scoped_prompt),
                HumanMessage(content=prompt),
            ]

            result = await self._stream_answer_with_retry(
                full_messages,
                node_name="spark_summary",
                config=config,
                fallback_text=fallback_text,
                retry_prompt=retry_prompt,
            )

            return {
                "messages": [result],
                "answer_text": result.content,
                "retrieved_profile_context": profile_context,
                "retrieved_memory_context": memory_context,
                "termination_reason": "spark_summary_done",
            }


    # ------------------------------------------------------------------
    # 节点: attachment_answer
    # ------------------------------------------------------------------

    async def _attachment_answer_node(
        self,
        state: TutorState,
        config: RunnableConfig,
    ) -> dict[str, Any]:
        """附件理解路径：Spark MAX 基于附件预分析结果回答。

        Args:
            state: LangGraph 状态。

        Returns:
            更新后的状态片段。
        """
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        attachments = state.get("attachments") or []
        messages = list(state.get("messages") or [])
        question = extract_question(messages)
        pre_analysis = state.get("attachment_analysis") or {}
        system_prompt = state.get("system_prompt", "")

        with node_timer(
            "attachment_answer",
            user=user_id,
            session=session_id,
            attachment_count=len(attachments),
        ):
            logger.info(
                "[TutorAgent] 附件回答 route=attachment_answer question=%s attachments=%s",
                truncate(question, 180),
                len(attachments),
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

            profile_context, memory_context = await self._load_learner_context(state, config)
            scoped_prompt = self._scoped_answer_prompt(
                system_prompt,
                question=question,
                profile_context=profile_context,
                memory_context=memory_context,
                diagram_enabled=bool(state.get("need_teaching_diagram", False)),
            )
            full_messages = build_messages(scoped_prompt, [HumanMessage(content=answer_prompt)])

            result = await self._stream_answer_with_retry(
                full_messages,
                node_name="attachment_answer",
                config=config,
            )

            return {
                "messages": [result],
                "answer_text": result.content,
                "retrieved_profile_context": profile_context,
                "retrieved_memory_context": memory_context,
                "attachment_analysis_result": {
                    "mode": "upload_preanalysis",
                    "analysis_context": full_context,
                },
                "termination_reason": "attachment_answer_done",
            }

    async def _teaching_diagram_generate_node(self, state: TutorState) -> TutorState:
        """基于本轮回答或上一轮教学对话生成教学图板。"""
        if not state.get("need_teaching_diagram", False):
            return state
        user_id = int(state.get("user_id") or 0)
        session_id = str(state.get("session_id") or "")
        with node_timer("teaching_diagram_generate", user=user_id, session=session_id):
            try:
                question = extract_question(state.get("messages") or [])
                answer = normalize_message_content(state.get("answer_text", "")).strip()
                if _diagram_only_requested(question):
                    question, answer = _previous_teaching_exchange(list(state.get("messages") or []))
                    state["termination_reason"] = "teaching_diagram_only_done"
                if not question or not answer:
                    state["teaching_diagram"] = None
                    state["teaching_diagram_error"] = "缺少问题或文字回答，跳过图解说明生成"
                    return state

                diagram = await self._generate_teaching_diagram(
                    question=question,
                    answer=answer,
                    state=state,
                )
                state["teaching_diagram"] = diagram.model_dump(mode="json")
                state["diagram_type"] = diagram.type
                state["teaching_diagram_error"] = None
                return state
            except Exception as exc:
                logger.exception("[TutorAgent] 教学图解节点失败")
                state["teaching_diagram"] = None
                state["teaching_diagram_error"] = str(exc)
                return state

    async def _generate_teaching_diagram(
        self,
        *,
        question: str,
        answer: str,
        state: TutorState,
    ) -> InsightCanvas:
        """使用注入的上下文生成经过验证的面向学习者的图板。"""
        profile_context = str(state.get("retrieved_profile_context", "")).strip()
        long_term_memory_context = str(state.get("retrieved_memory_context", "")).strip()
        session_summary_context = str(state.get("session_summary_context", "")).strip()
        attachment_context = str(state.get("attachment_analysis_context", "")).strip()
        context_parts = []
        if profile_context:
            context_parts.append(f"本轮按需读取的用户画像：\n{profile_context}")
        if long_term_memory_context:
            context_parts.append(f"本轮按需检索的长期学习依据：\n{long_term_memory_context}")
        if session_summary_context:
            context_parts.append(f"会话摘要上下文：\n{session_summary_context}")
        if attachment_context:
            context_parts.append(f"附件预分析上下文：\n{attachment_context}")
        preferred = state.get("diagram_type") or "由你选择最适合的类型"

        prompt = (
            f"学生问题：\n{question}\n\n"
            f"最终回答：\n{answer}\n\n"
            f"上下文：\n{chr(10).join(context_parts) if context_parts else '无额外上下文。'}\n\n"
            f"偏好图板类型：{preferred}\n\n"
            "请生成一张能辅助学生理解答案的 InsightCanvas 图板 JSON。"
        )
        return await self.llm.ainvoke_json(
            InsightCanvas,
            [SystemMessage(content=_get_prompt("teaching_diagram")), HumanMessage(content=prompt)],
            temperature=0.1,
        )

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

        logger.info(
            "[TutorAgent] 对话开始 message=%s attachments=%s enable_search=%s",
            truncate(current_message, 180),
            len(context.attachments),
            context.enable_search,
        )

        await self._ensure_graph()

        initial_state = prepare_tutor_state(context, history)

        full_reply = ""
        runtime_state: dict[str, Any] = dict(initial_state)
        graph_error_text = ""
        active_node = ""
        started_at = time.monotonic()
        first_token_ms: int | None = None

        try:
            # 在上下文中运行图
            with chat_runtime_context(context.user_id, context.session_id):
                async for event in self.graph.astream_events(initial_state, **_graph_stream_kwargs()):
                    kind = event.get("event", "")
                    name = event.get("name", "")

                    # 节点开始事件
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
                                {"stage": name, "message": "正在检索与问题相关的补充资料..."},
                            )
                        elif name == "direct_answer":
                            yield stream_event(
                                "status",
                                {"stage": name, "message": "正在组织回答..."},
                            )
                        elif name == "spark_summary":
                            yield stream_event(
                                "status",
                                {"stage": name, "message": "正在结合检索资料组织回答..."},
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

                    # 回答节点发出的稳定自定义流事件，避免完整生成后才一次性返回。
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

        # 发送错误事件
        if graph_error_text:
            yield stream_event("error", graph_error_text)
            yield stream_event("done", {"session_id": context.session_id, "error": True})
            return

        # 从状态中提取回复
        if not full_reply and runtime_state.get("execution_mode") != "diagram_only":
            messages = runtime_state.get("messages", [])
            if isinstance(messages, list):
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage):
                        full_reply = normalize_message_content(msg.content)
                        break

        teaching_diagram = runtime_state.get("teaching_diagram")

        # 独立的图解图板即使没有文字也是有效回复，无需补充文字。
        if not isinstance(teaching_diagram, dict) and is_unusable_reply_text(full_reply):
            yield stream_event("error", "模型未返回有效内容，请重试。")
            yield stream_event("done", {"session_id": context.session_id, "error": True})
            return

        if isinstance(teaching_diagram, dict):
            yield stream_event("diagram", teaching_diagram)

        # 发送完成事件
        yield stream_event(
            "done",
            {
                "session_id": context.session_id,
                "full_response": full_reply,
                "resource_mode": "none",
                "resource": None,
                "teaching_diagram": teaching_diagram,
                "resources": {"teaching_diagram": teaching_diagram, "video": None},
            },
        )
