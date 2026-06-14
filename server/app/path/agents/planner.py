import json
from typing import Any, Awaitable, Callable, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from loguru import logger

from app.chat.tools.search import duckduckgo_search, serp_search, spark_search, tavily_search
from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.path.schemas import AgentLearningPathPlan, AgentPathNode, AgentStage, CreateLearningPathRequest

ProgressCallback = Callable[[str, int, str], Awaitable[None]]

_SEARCH_FAILURE_MARKERS = (
    "搜索不可用",
    "搜索失败",
    "未找到相关搜索结果",
    "无可用搜索结果",
    "所有搜索引擎调用均失败",
)


class PathState(TypedDict):
    request: CreateLearningPathRequest
    profile: dict[str, Any]
    profile_markdown: str
    search_context: str
    progress_callback: ProgressCallback | None

    # Internal state
    strategy_report: str
    macro_stages: list[AgentStage]

    # Final output
    final_plan: AgentLearningPathPlan


class PathPlannerAgent:
    """课程级学习路径规划智能体 (LangGraph 多智能体实现)。"""

    def __init__(self, search_tools: list[Any] | None = None):
        self.llm = get_llm()
        self.search_tools = search_tools if search_tools is not None else [
            tavily_search,
            duckduckgo_search,
            serp_search,
            spark_search,
        ]
        self.max_search_tool_calls = 3
        self.system_prompt = prompts.get("path").get("planner_system")
        self.generate_graph = self._build_generate_graph()

    def _build_generate_graph(self):
        workflow = StateGraph(PathState)

        async def research_node(state: PathState) -> dict:
            logger.info("LangGraph [Path Research] starting...")
            if state["request"].enable_search:
                await emit_progress(state.get("progress_callback"), "researching", 30, "正在检索高价值参考资料")
            search_context = await self._collect_search_evidence(
                request=state["request"],
                profile=state["profile"],
            )
            logger.info("LangGraph [Path Research] finished, context length=%d", len(search_context))
            return {"search_context": search_context}

        async def node_strategist_node(state: PathState) -> dict:
            logger.info("LangGraph [Node Strategist] starting...")
            await emit_progress(state.get("progress_callback"), "analyzing", 44, "正在分析画像、目标与课程结构")
            await emit_progress(state.get("progress_callback"), "strategizing", 58, "正在生成阶段、节点与资源策略")
            profile_md = state.get("profile_markdown", "")
            if not profile_md:
                profile_md = json.dumps(state["profile"], ensure_ascii=False, indent=2)
            request_context = _format_request_context(state["request"])
            search_context = state.get("search_context", "")
            sys_msg = SystemMessage(content=prompts.get("path").get("planner_system"))
            human_msg = HumanMessage(content=f"{request_context}{search_context}\n\n学习者画像:\n{profile_md}")

            result = await self.llm.ainvoke_json(AgentLearningPathPlan, [sys_msg, human_msg])
            result = repair_generated_plan_from_macro_stages(
                plan=result,
                macro_stages=result.stages,
                request=state["request"],
                strategy_report=result.strategy_report,
            )
            logger.info(f"LangGraph [Node Strategist] finished with {len(result.nodes)} nodes.")
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
        """执行多智能体路径规划 (LangGraph版)。"""
        logger.info("PathPlannerAgent 开始规划路径 - Topic: {}", request.topic)
        try:
            initial_state = {
                "request": request,
                "profile": profile,
                "profile_markdown": profile_markdown,
                "search_context": "",
                "progress_callback": progress_callback,
                "strategy_report": "",
                "macro_stages": [],
                "final_plan": None
            }
            final_state = await self.generate_graph.ainvoke(initial_state)
            return final_state["final_plan"]
        except Exception as e:
            logger.error(f"PathPlannerAgent 路径规划失败: {str(e)}")
            raise e

    async def _collect_search_evidence(
        self,
        request: CreateLearningPathRequest,
        profile: dict[str, Any],
    ) -> str:
        """Let the LLM pick search tools, run them, return formatted text for the prompt."""
        if not request.enable_search or not self.search_tools:
            return ""

        try:
            bound_model = self.llm.model.bind_tools(self.search_tools)
            messages = _build_search_messages(request, profile)
            response = await self.llm.ainvoke(messages, model=bound_model, max_tokens=1000)
        except Exception as exc:
            logger.warning("[PathPlannerAgent] search tool setup failed: %s", exc)
            return ""

        tool_calls = list(getattr(response, "tool_calls", []) or [])[: self.max_search_tool_calls]
        if not tool_calls:
            direct = _message_content(response)
            if _is_usable(direct):
                return f"\n\n联网检索参考:\n{direct[:6000]}"
            return ""

        tools_by_name = {tool.name: tool for tool in self.search_tools}
        results = await _run_tool_calls(tool_calls, tools_by_name)
        usable = [r for r in results if _is_usable(r)]
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


def _format_request_context(request: CreateLearningPathRequest) -> str:
    current_knowledge = "、".join(request.current_knowledge) if request.current_knowledge else "未提供"
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
    request: CreateLearningPathRequest, profile: dict[str, Any]
) -> list[Any]:
    from langchain_core.messages import HumanMessage, SystemMessage

    profile_context = (
        json.dumps(profile, ensure_ascii=False, indent=2)
        if profile
        else "未提供"
    )
    return [
        SystemMessage(content=prompts.get("path").get("search_research_system")),
        HumanMessage(
            content=prompts.get("path").render(
                "search_research_user",
                request_context=_format_request_context(request),
                profile_context=profile_context,
            )
        ),
    ]


def _is_usable(result: object) -> bool:
    text = str(result or "").strip()
    if not text:
        return False
    return not any(marker in text for marker in _SEARCH_FAILURE_MARKERS)


def _message_content(message: Any) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, list):
        return "\n".join(str(item) for item in content)
    return str(content or "")


async def _run_tool_calls(tool_calls: list[Any], tools_by_name: dict[str, Any]) -> list[str]:
    """Execute search tool calls concurrently, return raw string results."""
    import asyncio

    async def _run_one(tool_call: Any) -> str:
        if isinstance(tool_call, dict):
            name, args = str(tool_call.get("name", "")), tool_call.get("args") or {}
        else:
            name, args = str(getattr(tool_call, "name", "")), getattr(tool_call, "args", {}) or {}
        tool = tools_by_name.get(name)
        if tool is None:
            return f"搜索工具不存在: {name}"
        try:
            result = await tool.ainvoke(dict(args))
            return str(result)
        except Exception as exc:
            logger.warning("[PathPlannerAgent] search tool failed: tool=%s error=%s", name, exc)
            return f"{name} 搜索失败: {exc}"

    return list(await asyncio.gather(*[_run_one(tc) for tc in tool_calls]))


def is_usable_search_result(result: object) -> bool:
    """Public alias kept for test backward compatibility."""
    return _is_usable(result)


def repair_generated_plan_from_macro_stages(
    *,
    plan: AgentLearningPathPlan,
    macro_stages: list[AgentStage],
    request: CreateLearningPathRequest,
    strategy_report: str,
) -> AgentLearningPathPlan:
    """Recover a structurally usable plan from the architect stage output.

    Schema now requires stages/nodes (min_length=1), so the normal path
    guarantees non-empty. This function handles edge cases where
    model_construct bypassed validation or stages/nodes are inconsistent.
    """
    if not plan.stages and macro_stages:
        plan.stages = list(macro_stages)

    # Derive stages from node stage_id values if stages still missing
    if not plan.stages and plan.nodes:
        seen: set[str] = set()
        derived: list[AgentStage] = []
        for node in plan.nodes:
            if node.stage_id not in seen:
                seen.add(node.stage_id)
                derived.append(AgentStage(
                    stage_id=node.stage_id,
                    title=node.title,
                    description=f"{node.title}阶段",
                ))
        plan.stages = derived

    if strategy_report:
        plan.strategy_report = strategy_report

    if not plan.adjustment_rationale:
        plan.adjustment_rationale = ["基于画像与路径规划阶段骨架生成学习路径"]

    if not plan.nodes and plan.stages:
        previous_node_id = ""
        nodes: list[AgentPathNode] = []
        for index, stage in enumerate(plan.stages, 1):
            node_id = f"{stage.stage_id}-core"
            difficulty = "beginner" if index == 1 else "intermediate"
            if index == len(plan.stages) and len(plan.stages) >= 3:
                difficulty = "advanced"
            node = AgentPathNode(
                node_id=node_id,
                stage_id=stage.stage_id,
                title=stage.title,
                prerequisites=[previous_node_id] if previous_node_id else [],
                mastery_target=stage.description or f"完成{stage.title}阶段学习",
                estimated_minutes=45,
                difficulty=difficulty,
                recommendation_reason=(
                    f"围绕「{request.goal}」的阶段目标生成，"
                    "用于保证路径规划结果可直接开始学习"
                ),
                priority=index * 10,
            )
            nodes.append(node)
            previous_node_id = node_id
        plan.nodes = nodes

    return plan


async def emit_progress(
    callback: ProgressCallback | None,
    status: str,
    progress: int,
    message: str,
) -> None:
    if callback is None:
        return
    await callback(status, progress, message)
