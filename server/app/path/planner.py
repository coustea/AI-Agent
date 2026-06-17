"""路径规划智能体 — 基于 LangGraph 的学习路径生成器。

核心流程（DAG）：
  research → strategist → END

research 节点：按需调用搜索工具，收集外部参考资料
strategist 节点：LLM 结合画像、搜索结果生成路径骨架（阶段 + 节点）

重要约束：
  1. 规划阶段只生成路径结构（stages + nodes），不生成教程、题目、PPT、代码、思维导图等资源。
  2. 当 LLM 结构化输出失败时，使用确定性兜底路径，避免前端直接进入 failed 状态。
"""

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
    AgentPathNode,
    AgentStage,
    CreateLearningPathRequest,
)

# 进度回调类型：(status, progress_pct, message) → None
ProgressCallback = Callable[[str, int, str], Awaitable[None]]

# 搜索结果中的失败标记词 — 匹配任一即认为该搜索无效
_SEARCH_FAILURE_MARKERS = (
    "搜索不可用",
    "搜索失败",
    "未找到相关搜索结果",
    "无可用搜索结果",
    "所有搜索引擎调用均失败",
)


class PathState(TypedDict):
    """LangGraph 状态图的全局状态，贯穿 research → strategist 全流程。"""

    request: CreateLearningPathRequest
    profile: dict[str, Any]
    profile_markdown: str
    search_context: str
    progress_callback: ProgressCallback | None

    # Final output
    final_plan: AgentLearningPathPlan | None


class PathPlannerAgent:
    """课程级学习路径规划智能体。"""

    def __init__(self, search_tools: list[Any] | None = None):
        self.llm = get_llm()
        # 可用的搜索工具列表 — LLM 在 research 阶段自主选择
        self.search_tools = search_tools if search_tools is not None else [
            tavily_search,
            duckduckgo_search,
            spark_search,
        ]
        # 单轮 research 最多执行的搜索工具调用次数
        self.max_search_tool_calls = 3
        self.system_prompt = prompts.get("path").get("planner_system")
        # 编译 LangGraph 工作流
        self.generate_graph = self._build_generate_graph()

    def _build_generate_graph(self):
        """构建 LangGraph DAG：research → strategist → END。"""
        workflow = StateGraph(PathState)

        async def research_node(state: PathState) -> dict[str, Any]:
            """联网研究节点 — 让 LLM 自主选择搜索工具收集参考资料。"""
            logger.info("LangGraph [Path Research] starting...")
            if state["request"].enable_search:
                await emit_progress(
                    state.get("progress_callback"),
                    "researching",
                    30,
                    "正在检索高价值参考资料",
                )
            # 执行混合搜索，返回格式化的参考文本
            search_context = await self._collect_search_evidence(
                request=state["request"],
                profile=state["profile"],
            )
            logger.info("LangGraph [Path Research] finished, context length=%d", len(search_context))
            return {"search_context": search_context}

        async def node_strategist_node(state: PathState) -> dict[str, Any]:
            """策略规划节点 — 结合画像和搜索结果生成路径骨架。"""
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

            # 优先使用预渲染的 profile_markdown，否则从 dict 序列化
            profile_md = state.get("profile_markdown", "")
            if not profile_md:
                profile_md = json.dumps(state["profile"], ensure_ascii=False, indent=2)

            request_context = _format_request_context(state["request"])
            search_context = state.get("search_context", "")
            messages = _build_planner_messages(
                request_context=request_context,
                search_context=search_context,
                profile_markdown=profile_md,
            )

            # LLM 结构化输出 → AgentLearningPathPlan（只含 title / eta_days / confidence / stages / nodes）
            # resource_policy 不强制由 LLM 生成，后续由 normalize_path_plan 确定性补全。
            result = await self.llm.ainvoke_json(
                AgentLearningPathPlan,
                messages,
                max_tokens=4096,
            )

            # 修复可能的结构缺陷（空 stages/nodes、不一致的引用）
            result = repair_generated_plan_from_macro_stages(
                plan=result,
                macro_stages=result.stages,
                request=state["request"],
            )
            logger.info("LangGraph [Node Strategist] finished with %d nodes.", len(result.nodes))
            return {"final_plan": result}

        # 注册两个节点并连接 DAG
        workflow.add_node("research", research_node)
        workflow.add_node("strategist", node_strategist_node)

        # DAG 边：START → research → strategist → END
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
        """执行学习路径规划。"""
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
            logger.error("PathPlannerAgent 路径规划失败，使用兜底路径: {}", str(exc))
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
        """让 LLM 自主选择搜索工具并执行，返回格式化的参考文本。"""
        # 未启用搜索或无可用工具时直接返回空
        if not request.enable_search or not self.search_tools:
            return ""

        try:
            # 绑定搜索工具到 LLM，让模型自主决定调用哪个搜索引擎
            bound_model = self.llm.model.bind_tools(self.search_tools)
            messages = _build_search_messages(request, profile)
            response = await self.llm.ainvoke(messages, model=bound_model, max_tokens=1000)
        except Exception as exc:
            logger.warning("[PathPlannerAgent] search tool setup failed: %s", exc)
            return ""

        # 提取 LLM 的工具调用请求，限制最多 max_search_tool_calls 个
        tool_calls = list(getattr(response, "tool_calls", []) or [])[: self.max_search_tool_calls]
        if not tool_calls:
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
    """构建路径规划阶段的消息，强约束只输出 AgentLearningPathPlan 根 JSON。"""
    sys_msg = SystemMessage(content=prompts.get("path").get("planner_system"))
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
    """将路径创建请求格式化为 LLM 可读的上下文文本。"""
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
    request: CreateLearningPathRequest,
    profile: dict[str, Any],
) -> list[Any]:
    """构建搜索研究阶段的 LLM 消息列表。"""
    from langchain_core.messages import HumanMessage, SystemMessage

    # 将画像序列化为 JSON 文本注入 prompt
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


def is_usable_search_result(result: object) -> bool:
    """判断搜索结果是否可用（非空且不含失败标记词）。"""
    text = str(result or "").strip()
    if not text:
        return False
    return not any(marker in text for marker in _SEARCH_FAILURE_MARKERS)


def _message_content(message: Any) -> str:
    """从 LLM 响应消息中提取文本内容（兼容 str 和 list 类型）。"""
    content = getattr(message, "content", message)
    if isinstance(content, list):
        return "\n".join(str(item) for item in content)
    return str(content or "")


async def _run_tool_calls(tool_calls: list[Any], tools_by_name: dict[str, Any]) -> list[str]:
    """并发执行搜索工具调用，返回原始结果文本列表。"""
    import asyncio

    async def _run_one(tool_call: Any) -> str:
        """执行单个搜索工具调用，捕获异常返回错误信息。"""
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
            logger.warning("[PathPlannerAgent] search tool failed: tool=%s error=%s", name, exc)
            return f"{name} 搜索失败: {exc}"

    # 使用 asyncio.gather 并发执行所有搜索调用
    return list(await asyncio.gather(*[_run_one(tc) for tc in tool_calls]))





def repair_generated_plan_from_macro_stages(
    *,
    plan: AgentLearningPathPlan,
    macro_stages: list[AgentStage],
    request: CreateLearningPathRequest,
) -> AgentLearningPathPlan:
    """修复 LLM 生成的路径规划中的结构缺陷。

    处理场景：
      1. stages 为空但 macro_stages 有值 → 从 macro_stages 补充
      2. stages 为空但 nodes 有值 → 从 nodes 的 stage_id 推导 stages
      3. nodes 为空但 stages 有值 → 为每个 stage 生成默认节点
    """
    if not plan.stages and macro_stages:
        plan.stages = list(macro_stages)

    if not plan.stages and plan.nodes:
        seen: set[str] = set()
        derived: list[AgentStage] = []
        for node in plan.nodes:
            if node.stage_id not in seen:
                seen.add(node.stage_id)
                derived.append(AgentStage(stage_id=node.stage_id, title=node.title))
        plan.stages = derived

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
                difficulty=difficulty,
                priority=index * 10,
            )
            nodes.append(node)
            previous_node_id = node_id
        plan.nodes = nodes

    return plan


def build_fallback_path_plan(request: CreateLearningPathRequest) -> AgentLearningPathPlan:
    """LLM 结构化输出失败时的确定性兜底路径。"""
    topic = (request.topic or request.goal or "课程学习").strip()
    goal = (request.goal or topic).strip()

    stages = [
        AgentStage(stage_id="stage-1", title="基础认知与前置补齐"),
        AgentStage(stage_id="stage-2", title="核心机制与高频考点"),
        AgentStage(stage_id="stage-3", title="综合应用与复习巩固"),
    ]

    nodes = [
        AgentPathNode(
            node_id="node-1", stage_id="stage-1",
            title=f"{topic}学习地图与核心术语",
            prerequisites=[], difficulty="beginner", priority=1,
        ),
        AgentPathNode(
            node_id="node-2", stage_id="stage-1",
            title="前置基础补齐",
            prerequisites=["node-1"], difficulty="beginner", priority=2,
        ),
        AgentPathNode(
            node_id="node-3", stage_id="stage-2",
            title="核心概念与结构关系",
            prerequisites=["node-2"], difficulty="intermediate", priority=3,
        ),
        AgentPathNode(
            node_id="node-4", stage_id="stage-2",
            title="关键流程与典型机制",
            prerequisites=["node-3"], difficulty="intermediate", priority=4,
        ),
        AgentPathNode(
            node_id="node-5", stage_id="stage-2",
            title="易错点与薄弱点专项巩固",
            prerequisites=["node-4"], difficulty="intermediate", priority=5,
        ),
        AgentPathNode(
            node_id="node-6", stage_id="stage-3",
            title="综合练习与知识总结",
            prerequisites=["node-5"], difficulty="advanced", priority=6,
        ),
    ]

    return AgentLearningPathPlan(title=f"{topic}个性化学习路径", stages=stages, nodes=nodes)


async def emit_progress(
    callback: ProgressCallback | None,
    status: str,
    progress: int,
    message: str,
) -> None:
    """安全调用进度回调 — callback 为 None 时跳过。"""
    if callback is None:
        return
    await callback(status, progress, message)
