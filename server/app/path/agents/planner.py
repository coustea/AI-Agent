from __future__ import annotations

import json
from typing import Any, Awaitable, Callable, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from loguru import logger

from app.chat.tools.search import duckduckgo_search, spark_search, tavily_search
from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.path.schemas import (
    AgentLearningPathPlan,
    CreateLearningPathRequest,
)
from app.path.workflows.plan_workflow import (
    build_fallback_path_plan,
    repair_generated_plan_from_macro_stages,
)

# 进度回调类型：(状态, 进度百分比, 消息) → None
ProgressCallback = Callable[[str, int, str], Awaitable[None]]

# 搜索结果无效标记 — 出现这些文本时判定搜索失败
_SEARCH_FAILURE_MARKERS = (
    "搜索不可用",
    "搜索失败",
    "未找到相关搜索结果",
    "无可用搜索结果",
    "所有搜索引擎调用均失败",
)


class PathState(TypedDict):
    """LangGraph 状态图中 research → strategist 的全局状态。"""

    request: CreateLearningPathRequest
    profile: dict[str, Any]
    profile_markdown: str
    search_context: str
    progress_callback: ProgressCallback | None
    final_plan: AgentLearningPathPlan | None


class PathPlannerAgent:
    """课程级学习路径规划智能体。

    使用 LangGraph 编排两个阶段：
    1. research — 可选的联网检索，收集参考资料
    2. strategist — 基于画像和检索结果，生成结构化路径规划

    如果 LLM 规划失败，自动降级为兜底路径。
    """

    def __init__(self, search_tools: list[Any] | None = None):
        self.llm = get_llm()
        # 默认搜索工具链：Tavily → DuckDuckGo → Spark
        self.search_tools = search_tools if search_tools is not None else [
            tavily_search,
            duckduckgo_search,
            spark_search,
        ]
        self.max_search_tool_calls = 3  # 最大并行搜索调用数
        self.system_prompt = prompts.get("path").get("planner_system")
        self.generate_graph = self._build_generate_graph()

    def _build_generate_graph(self):
        """构建 LangGraph 状态图：START → research → strategist → END。"""
        workflow = StateGraph(PathState)

        async def research_node(state: PathState) -> dict[str, Any]:
            """研究节点 — 调用搜索工具收集参考资料。"""
            logger.info("LangGraph [Path Research] starting...")
            if state["request"].enable_search:
                await emit_progress(
                    state.get("progress_callback"),
                    "researching",
                    30,
                    "正在检索高价值参考资料",
                )
            search_context = await self._collect_search_evidence(
                request=state["request"],
                profile=state["profile"],
            )
            logger.info(
                "LangGraph [Path Research] finished, context length=%d",
                len(search_context),
            )
            return {"search_context": search_context}

        async def node_strategist_node(state: PathState) -> dict[str, Any]:
            """策略节点 — 基于画像和检索结果生成路径规划。"""
            logger.info("LangGraph [Node Strategist] starting...")
            await emit_progress(
                state.get("progress_callback"),
                "analyzing",
                44,
                "正在分析画像、目标与课程结构",
            )
            await emit_progress(
                state.get("progress_callback"),
                "strategizing",
                58,
                "正在生成阶段与学习节点",
            )

            # 优先使用预渲染的画像 Markdown，降级为 JSON 序列化
            profile_md = state.get("profile_markdown", "")
            if not profile_md:
                profile_md = json.dumps(
                    state["profile"], ensure_ascii=False, indent=2
                )

            request_context = _format_request_context(state["request"])
            search_context = state.get("search_context", "")
            messages = _build_planner_messages(
                request_context=request_context,
                search_context=search_context,
                profile_markdown=profile_md,
            )

            result = await self.llm.ainvoke_json(
                AgentLearningPathPlan,
                messages,
                max_tokens=4096,
            )

            # 修复 LLM 输出中可能缺失的 stages/nodes 对齐
            result = repair_generated_plan_from_macro_stages(
                plan=result,
                macro_stages=result.stages,
                request=state["request"],
            )
            logger.info(
                "LangGraph [Node Strategist] finished with %d nodes.",
                len(result.nodes),
            )
            return {"final_plan": result}

        workflow.add_node("research", research_node)
        workflow.add_node("strategist", node_strategist_node)
        workflow.add_edge(START, "research")
        workflow.add_edge("research", "strategist")
        workflow.add_edge("strategist", END)

        return workflow.compile()

    async def generate_plan(
        self,
        request: CreateLearningPathRequest,
        profile: dict[str, Any],
        progress_callback: ProgressCallback | None = None,
        profile_markdown: str = "",
    ) -> AgentLearningPathPlan:
        """执行路径规划：运行 LangGraph 状态图，失败时降级为兜底路径。"""
        logger.info("PathPlannerAgent 开始规划路径 - Topic: {}", request.topic)
        try:
            initial_state: PathState = {
                "request": request,
                "profile": profile,
                "profile_markdown": profile_markdown,
                "search_context": "",
                "progress_callback": progress_callback,
                "final_plan": None,
            }
            final_state = await self.generate_graph.ainvoke(initial_state)
            plan = final_state.get("final_plan")
            if plan is None:
                raise ValueError("路径规划未返回 final_plan")
            return plan
        except Exception as exc:
            logger.error(
                "PathPlannerAgent 路径规划失败，使用兜底路径: {}", str(exc)
            )
            await emit_progress(
                progress_callback,
                "fallback",
                76,
                "结构化规划失败，正在生成稳定兜底路径",
            )
            return build_fallback_path_plan(request)

    async def _collect_search_evidence(
        self,
        request: CreateLearningPathRequest,
        profile: dict[str, Any],
    ) -> str:
        """调用搜索工具收集联网参考资料，返回拼接后的文本。"""
        if not request.enable_search or not self.search_tools:
            return ""

        try:
            bound_model = self.llm.model.bind_tools(self.search_tools)
            messages = _build_search_messages(request, profile)
            response = await self.llm.ainvoke(
                messages, model=bound_model, max_tokens=1000
            )
        except Exception as exc:
            logger.warning(
                "[PathPlannerAgent] search tool setup failed: %s", exc
            )
            return ""

        # 从 LLM 响应中提取工具调用（最多 max_search_tool_calls 个）
        tool_calls = list(
            getattr(response, "tool_calls", []) or []
        )[: self.max_search_tool_calls]
        if not tool_calls:
            # 如果没有工具调用，检查响应内容是否为有效搜索结果
            direct = _message_content(response)
            if is_usable_search_result(direct):
                return f"\n\n联网检索参考:\n{direct[:6000]}"
            return ""

        tools_by_name = {tool.name: tool for tool in self.search_tools}
        results = await _run_tool_calls(tool_calls, tools_by_name)
        usable = [r for r in results if is_usable_search_result(r)]
        if not usable:
            return ""

        combined = "\n\n".join(usable)
        if len(combined) > 6000:
            combined = combined[:6000]
        return (
            "\n\n联网检索参考:\n"
            "以下内容只作为课程路径规划的外部参考。必须优先服从用户目标、画像和已掌握知识；"
            "不得编造检索资料未支持的事实，不要把搜索摘要中的广告、无关页面或不确定内容写成课程结论。\n\n"
            + combined
        )


def _build_planner_messages(
    *,
    request_context: str,
    search_context: str,
    profile_markdown: str,
) -> list[Any]:
    """构建路径规划的 LLM 消息列表（系统提示 + 用户请求）。"""
    sys_msg = SystemMessage(
        content=prompts.get("path").get("planner_system")
    )
    human_msg = HumanMessage(
        content=(
            "请根据以下信息生成学习路径 JSON。\n\n"
            f"用户请求：\n{request_context}\n\n"
            f"联网参考：\n{search_context or '未启用或无可用参考'}\n\n"
            f"学习者画像：\n{profile_markdown or '未提供'}\n\n"
            "再次强调：只输出符合 schema 的 JSON 根对象，不要输出 Markdown，不要输出解释文字。"
        )
    )
    return [sys_msg, human_msg]


def _format_request_context(request: CreateLearningPathRequest) -> str:
    """将请求参数格式化为人类可读的上下文文本。"""
    current_knowledge = (
        "、".join(request.current_knowledge)
        if request.current_knowledge
        else "未提供"
    )
    preferences = (
        json.dumps(request.preferences, ensure_ascii=False, indent=2)
        if request.preferences
        else "未提供"
    )
    return (
        f"学习目标: {request.goal}\n"
        f"学习主题: {request.topic or '未提供'}\n"
        f"所属模块: {request.module}\n"
        f"已掌握知识: {current_knowledge}\n"
        f"学习偏好:\n{preferences}"
    )


def _build_search_messages(
    request: CreateLearningPathRequest,
    profile: dict[str, Any],
) -> list[Any]:
    """构建搜索检索的 LLM 消息列表。"""
    profile_context = (
        json.dumps(profile, ensure_ascii=False, indent=2)
        if profile
        else "未提供"
    )
    return [
        SystemMessage(
            content=prompts.get("path").get("search_research_system")
        ),
        HumanMessage(
            content=prompts.get("path").render(
                "search_research_user",
                request_context=_format_request_context(request),
                profile_context=profile_context,
            )
        ),
    ]


def is_usable_search_result(result: object) -> bool:
    """判断搜索结果是否可用（非空且不包含失败标记）。"""
    text = str(result or "").strip()
    if not text:
        return False
    return not any(marker in text for marker in _SEARCH_FAILURE_MARKERS)


def _message_content(message: Any) -> str:
    """从 LLM 消息对象中提取文本内容。"""
    content = getattr(message, "content", message)
    if isinstance(content, list):
        return "\n".join(str(item) for item in content)
    return str(content or "")


async def _run_tool_calls(
    tool_calls: list[Any], tools_by_name: dict[str, Any]
) -> list[str]:
    """并行执行多个搜索工具调用。"""
    import asyncio

    async def _run_one(tool_call: Any) -> str:
        """执行单个工具调用，返回结果文本。"""
        if isinstance(tool_call, dict):
            name = str(tool_call.get("name", ""))
            args = tool_call.get("args") or {}
        else:
            name = str(getattr(tool_call, "name", ""))
            args = getattr(tool_call, "args", {}) or {}
        tool = tools_by_name.get(name)
        if tool is None:
            return f"搜索工具不存在: {name}"
        try:
            result = await tool.ainvoke(dict(args))
            return str(result)
        except Exception as exc:
            logger.warning(
                "[PathPlannerAgent] search tool failed: tool=%s error=%s",
                name,
                exc,
            )
            return f"{name} 搜索失败: {exc}"

    return list(await asyncio.gather(*[_run_one(tc) for tc in tool_calls]))


async def emit_progress(
    callback: ProgressCallback | None,
    status: str,
    progress: int,
    message: str,
) -> None:
    """触发进度回调（如果回调存在）。"""
    if callback is None:
        return
    await callback(status, progress, message)
