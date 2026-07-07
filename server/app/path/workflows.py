"""路径规划与学习流程的工作流与智能体实现。

包含：
1. 路径规划智能体 (PathPlannerAgent) 与 LangGraph 规划工作流
2. 节点学习智能体 (NodeLearningAgent) — 生成教程和测验题目
3. 节点学习工作流 (get_learn_workflow) — 教程/测验/资源的完整流程
4. 兜底与修复函数 (build_fallback_plan, repair_plan)

工作流拓扑：
- 路径规划：START → research → strategist → END
- 节点学习：START → load_context → [phase路由] → gen_tutorial/gen_questions/score_answers/gen_resource → END
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from loguru import logger as loguru_logger
from sqlmodel import col, select

from app.config import PATH_PASS_SCORE, PATH_QUIZ_SIZE
from app.infra.logging import get_logger
from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.infra.models import (
    LearningPath,
    PathNode,
    PathNodeQuestion,
    PathNodeResource,
    PathNodeTutorial,
)
from app.profile.service import get_profile_service
from app.resource.path_helpers import generate_path_node_resource
from app.resource.schemas import NodeInput
from app.shared.research import ResearchAgent, ResearchTask

# 从本地合并后的 schemas 导入
from app.path.schemas import (
    LearningPlan,
    PlanNode,
    AgentStage,
    PathRequest,
    LearnState,
    AgentQuestionSet,
)

logger = get_logger(__name__)

# ======================================================================
# 1. 兜底与修复规划函数
# ======================================================================

def repair_plan(*, plan: LearningPlan, macro_stages: list[AgentStage], request: PathRequest) -> LearningPlan:
    """修复 LLM 生成的路径规划，确保 stages 和 nodes 正确对齐。

    处理场景：
    - plan.stages 为空但 macro_stages 有内容 → 复制 macro_stages
    - plan.stages 为空但 nodes 有内容 → 从 nodes 推导 stages
    - plan.nodes 为空但 stages 有内容 → 从 stages 生成默认 nodes
    """
    if not plan.stages and macro_stages:
        plan.stages = list(macro_stages)

    if not plan.stages and plan.nodes:
        seen: set[str] = set()
        derived: list[AgentStage] = []
        for node in plan.nodes:
            if node.stage_id not in seen:
                seen.add(node.stage_id)
                derived.append(
                    AgentStage(stage_id=node.stage_id, title=node.title)
                )
        plan.stages = derived

    if not plan.nodes and plan.stages:
        previous_node_id = ""
        nodes: list[PlanNode] = []
        for index, stage in enumerate(plan.stages, 1):
            node_id = f"{stage.stage_id}-core"
            difficulty = "beginner" if index == 1 else "intermediate"
            if index == len(plan.stages) and len(plan.stages) >= 3:
                difficulty = "advanced"
            node = PlanNode(
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


def build_fallback_plan(request: PathRequest) -> LearningPlan:
    """构建兜底学习路径 — 当 LLM 结构化规划失败时使用。

    生成 3 个阶段、6 个节点的标准学习路径结构。
    """
    topic = (request.topic or request.goal or "课程学习").strip()
    goal = (request.goal or topic).strip()

    stages = [
        AgentStage(stage_id="stage-1", title="基础认知与前置补齐"),
        AgentStage(stage_id="stage-2", title="核心机制与高频考点"),
        AgentStage(stage_id="stage-3", title="综合应用与复习巩固"),
    ]

    nodes = [
        PlanNode(
            node_id="node-1",
            stage_id="stage-1",
            title=f"{topic}学习地图与核心术语",
            prerequisites=[],
            difficulty="beginner",
            priority=1,
        ),
        PlanNode(
            node_id="node-2",
            stage_id="stage-1",
            title="前置基础补齐",
            prerequisites=["node-1"],
            difficulty="beginner",
            priority=2,
        ),
        PlanNode(
            node_id="node-3",
            stage_id="stage-2",
            title="核心概念与结构关系",
            prerequisites=["node-2"],
            difficulty="intermediate",
            priority=3,
        ),
        PlanNode(
            node_id="node-4",
            stage_id="stage-2",
            title="关键流程与典型机制",
            prerequisites=["node-3"],
            difficulty="intermediate",
            priority=4,
        ),
        PlanNode(
            node_id="node-5",
            stage_id="stage-2",
            title="易错点与薄弱点专项巩固",
            prerequisites=["node-4"],
            difficulty="intermediate",
            priority=5,
        ),
        PlanNode(
            node_id="node-6",
            stage_id="stage-3",
            title="综合练习与知识总结",
            prerequisites=["node-5"],
            difficulty="advanced",
            priority=6,
        ),
    ]

    return LearningPlan(
        title=f"{topic}个性化学习路径", stages=stages, nodes=nodes
    )


# ======================================================================
# 2. 路径规划智能体
# ======================================================================

# 进度回调函数类型
ProgressCallback = Callable[[str, int, str], Awaitable[None]]


# LangGraph 规划工作流状态
class PathState(TypedDict):
    """LangGraph 状态图中 research → strategist 的全局状态。"""
    request: PathRequest
    profile: dict[str, Any]
    profile_markdown: str
    search_context: str
    progress_callback: ProgressCallback | None
    final_plan: LearningPlan | None


class PathPlannerAgent:
    """课程级学习路径规划智能体。

    使用 LangGraph 编排 research → strategist 两个阶段：
    - research：联网检索课程结构参考
    - strategist：基于画像和目标生成阶段与节点
    """

    def __init__(self) -> None:
        self.llm = get_llm()
        self.research_agent = ResearchAgent()
        self.system_prompt = prompts.get("path").get("planner_system")
        self.generate_graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(PathState)

        async def research_node(state: PathState) -> dict[str, Any]:
            loguru_logger.info("LangGraph [Path Research] starting...")
            if state["request"].enable_search:
                await emit_progress(
                    state.get("progress_callback"),
                    "researching",
                    30,
                    "正在检索高价值参考资料",
                )
            search_context = await self._search(
                request=state["request"],
                profile=state["profile"],
            )
            loguru_logger.info(
                "LangGraph [Path Research] finished, context length=%d",
                len(search_context),
            )
            return {"search_context": search_context}

        async def node_strategist_node(state: PathState) -> dict[str, Any]:
            loguru_logger.info("LangGraph [Node Strategist] starting...")
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

            use_profile = state["request"].preferences.get("use_profile", True)
            if use_profile is False or use_profile == "false":
                profile_md = "用户已关闭个人画像融合，请勿结合画像数据，仅根据学习主题与目标进行最优路径推演规划。"
            else:
                profile_md = state.get("profile_markdown", "")
                if not profile_md:
                    profile_md = json.dumps(
                        state["profile"], ensure_ascii=False, indent=2
                    )

            request_context = _format_request(state["request"])
            search_context = state.get("search_context", "")
            messages = _build_planner_messages(
                request_context=request_context,
                search_context=search_context,
                profile_markdown=profile_md,
            )

            result = await self.llm.ainvoke_json(
                LearningPlan,
                messages,
                max_tokens=4096,
            )

            result = repair_plan(
                plan=result,
                macro_stages=result.stages,
                request=state["request"],
            )
            loguru_logger.info(
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

    async def generate_plan(self, request: PathRequest, profile: dict[str, Any], progress_callback: ProgressCallback | None = None, profile_markdown: str = "") -> LearningPlan:
        """执行路径规划工作流，返回 LearningPlan。

        失败时自动降级到 build_fallback_plan。
        """
        loguru_logger.info("PathPlannerAgent 开始规划路径 - Topic: {}", request.topic)
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
            loguru_logger.error(
                "PathPlannerAgent 路径规划失败，使用兜底路径: {}", str(exc)
            )
            await emit_progress(
                progress_callback,
                "fallback",
                76,
                "结构化规划失败，正在生成稳定兜底路径",
            )
            return build_fallback_plan(request)

    @staticmethod
    def _format_sources(report: "ResearchReport") -> str:
        """将 ResearchReport.sources 格式化为纯文本上下文。"""
        if not report.sources:
            return ""
        parts = []
        for s in report.sources:
            entry = s.title
            if s.url:
                entry += f"\n链接: {s.url}"
            if s.summary:
                entry += f"\n摘要: {s.summary}"
            parts.append(entry)
        return "\n\n".join(parts)

    async def _search(
        self,
        request: PathRequest,
        profile: dict[str, Any],
    ) -> str:
        if not request.enable_search:
            return ""

        try:
            query = f"{request.topic or request.goal} 学习路径 课程结构"
            report = await self.research_agent.run(
                ResearchTask(
                    query=query,
                    objective="为学习路径规划收集课程结构、知识点和教学参考",
                    sources={"web"},
                    depth="standard",
                )
            )
            context = self._format_sources(report)
            if not context:
                return ""

            return (
                "\n\n联网检索参考:\n"
                "以下内容只作为课程路径规划的外部参考。必须优先服从用户目标、画像和已掌握知识；"
                "不得编造检索资料未支持的事实，不要把搜索摘要中的广告、无关页面或不确定内容写成课程结论。\n\n"
                + context[:6000]
            )
        except Exception as exc:
            loguru_logger.warning(
                "[PathPlannerAgent] ResearchAgent search failed: %s", exc
            )
            return ""


def _build_planner_messages(
    *,
    request_context: str,
    search_context: str,
    profile_markdown: str,
) -> list[Any]:
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


def _format_request(request: PathRequest) -> str:
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



async def emit_progress(
    callback: ProgressCallback | None,
    status: str,
    progress: int,
    message: str,
) -> None:
    if callback is None:
        return
    await callback(status, progress, message)


# ======================================================================
# 3. 节点学习智能体
# ======================================================================

class NodeLearningAgent:
    """节点学习智能体 — 调用 LLM 生成节点教程内容和测验题目。

    主要方法：
    - generate_tutorial：生成教程 Markdown
    - generate_questions：生成 5 道测验题目
    """

    def __init__(self) -> None:
        self.llm = get_llm()

    async def generate_tutorial(
        self,
        *,
        path_goal: str,
        node_title: str,
        mastery_target: str,
        tutorial_type: str,
        weak_knowledge_points: list[str],
        profile_markdown: str = "",
    ) -> dict[str, Any]:
        weak_points_section = ""
        if weak_knowledge_points:
            weak_points_section = (
                f"重点围绕这些薄弱知识点强化：{', '.join(weak_knowledge_points)}"
            )
        profile_section = (
            f"学习者画像:\n{profile_markdown[:2000]}" if profile_markdown else ""
        )
        prompt = prompts.get("path").render(
            "tutorial",
            path_goal=path_goal,
            node_title=node_title,
            mastery_target=mastery_target,
            tutorial_type=tutorial_type,
            weak_points_section=weak_points_section,
            profile_section=profile_section,
        )
        prompt = prompt
        response = await self.llm.ainvoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        return {
            "title": f"{node_title} - {tutorial_type}",
            "summary": tutorial_type,
            "content_markdown": content,
            "knowledge_points": [node_title],
        }

    async def generate_questions(
        self,
        *,
        path_goal: str,
        node_title: str,
        mastery_target: str,
        tutorial_title: str,
        tutorial_summary: str,
        round_no: int,
    ) -> list[dict[str, Any]]:
        prompt = prompts.get("path").render(
            "question_generation",
            path_goal=path_goal,
            node_title=node_title,
            mastery_target=mastery_target,
            tutorial_title=tutorial_title,
            tutorial_summary=tutorial_summary,
            round_no=round_no,
        )
        result = await self.llm.ainvoke_json(AgentQuestionSet, prompt)
        questions = result.questions if hasattr(result, "questions") else []
        normalized: list[dict[str, Any]] = []
        for item in questions:
            choice = dict(getattr(item, "choice", {}) or {})
            normalized.append(
                {
                    "question": getattr(item, "question", ""),
                    "choice": choice,
                    "answer": str(getattr(item, "answer", "")),
                    "analysis": getattr(item, "analysis", ""),
                    "knowledge_points": list(
                        getattr(item, "knowledge_points", []) or [node_title]
                    ),
                    "type": getattr(item, "type", "single_choice"),
                }
            )
        return normalized


# ======================================================================
# 4. 节点学习工作流
# ======================================================================

# 节点完成状态集合
COMPLETED_NODE_STATUSES = frozenset({"completed", "completed_with_gaps"})

# 节点活跃状态集合
ACTIVE_NODE_STATUSES = frozenset({"available", "in_progress", "remediation", "reinforced"})


def _route_by_phase(state: LearnState) -> str:
    """路由函数：根据 phase 字段决定下一个节点。"""
    return state["phase"]


def _route_by_outcome(state: LearnState) -> str:
    """路由函数：根据测验结果决定下一步（补救/强化/解锁）。"""
    outcome = state.get("outcome", "completed")
    if outcome == "remediation":
        return "gen_remediation_tutorial"
    if outcome == "completed_with_gaps" and state.get("tutorial_type") == "reinforced":
        return "gen_reinforced_tutorial"
    return "unlock_progress"


def _build_learn_workflow() -> StateGraph:
    """构建节点学习 LangGraph 工作流。

    拓扑：
      START → load_context → [phase 路由]
        - start: gen_tutorial → persist → END
        - questions: gen_questions → persist → END
        - quiz: score_answers → advance_state → [outcome 路由] → END
        - resource: gen_resource → persist → END
    """
    wf = StateGraph(LearnState)

    wf.add_node("load_context", node_load_context)
    wf.add_node("gen_primary_tutorial", node_generate_tutorial)
    wf.add_node("persist_tutorial_start", node_persist_tutorial_and_mark)
    wf.add_node("gen_questions", node_generate_questions)
    wf.add_node("persist_questions", node_persist_questions)
    wf.add_node("score_answers", node_score_answers)
    wf.add_node("advance_state", node_advance_state)
    wf.add_node("unlock_progress", node_unlock_and_update_progress)
    wf.add_node("gen_remediation_tutorial", node_generate_tutorial)
    wf.add_node("persist_remediation_tutorial", node_persist_tutorial_and_mark)
    wf.add_node("gen_reinforced_tutorial", node_generate_tutorial)
    wf.add_node("persist_reinforced_tutorial", node_persist_tutorial_and_mark)
    wf.add_node("record_event", node_record_quiz_event)
    wf.add_node("gen_resource", node_generate_resource)
    wf.add_node("persist_resource", node_persist_resource)

    wf.add_edge(START, "load_context")

    wf.add_conditional_edges(
        "load_context",
        _route_by_phase,
        {
            "start": "gen_primary_tutorial",
            "questions": "gen_questions",
            "quiz": "score_answers",
            "resource": "gen_resource",
        },
    )

    wf.add_edge("gen_primary_tutorial", "persist_tutorial_start")
    wf.add_edge("persist_tutorial_start", END)

    wf.add_edge("gen_questions", "persist_questions")
    wf.add_edge("persist_questions", END)

    wf.add_edge("score_answers", "advance_state")
    wf.add_conditional_edges(
        "advance_state",
        _route_by_outcome,
        {
            "gen_remediation_tutorial": "gen_remediation_tutorial",
            "gen_reinforced_tutorial": "gen_reinforced_tutorial",
            "unlock_progress": "unlock_progress",
        },
    )

    wf.add_edge("gen_remediation_tutorial", "persist_remediation_tutorial")
    wf.add_edge("persist_remediation_tutorial", "record_event")
    wf.add_edge("record_event", END)

    wf.add_edge("gen_reinforced_tutorial", "persist_reinforced_tutorial")
    wf.add_edge("persist_reinforced_tutorial", "unlock_progress")

    wf.add_edge("unlock_progress", "record_event")

    wf.add_edge("gen_resource", "persist_resource")
    wf.add_edge("persist_resource", END)

    return wf.compile()


_learn_workflow: StateGraph | None = None


def get_learn_workflow() -> StateGraph:
    """获取节点学习工作流的编译后状态图（单例）。"""
    global _learn_workflow
    if _learn_workflow is None:
        _learn_workflow = _build_learn_workflow()
    return _learn_workflow


# ── 工作流节点函数 ──────────────────────────────────────────────────────────

async def node_load_context(state: LearnState) -> dict:
    """加载节点上下文：PathNode、LearningPath、教程列表、学习者画像。"""
    session = state["session"]
    user_id = state["user_id"]
    node_id = state["node_id"]

    node = await session.get(PathNode, node_id)
    if node is None or node.user_id != user_id:
        return {"error": "路径节点不存在"}

    path = await session.get(LearningPath, node.path_id)
    if path is None:
        return {"error": "学习路径不存在"}

    stmt = (
        select(PathNodeTutorial)
        .where(PathNodeTutorial.node_id == node_id)
        .order_by(
            col(PathNodeTutorial.version_no).asc(),
            col(PathNodeTutorial.id).asc(),
        )
    )
    tutorials = list((await session.exec(stmt)).all())
    current_tutorial = next((t for t in tutorials if t.is_current), None)

    try:
        profile_service = get_profile_service()
        profile_markdown = await profile_service.build_profile_markdown(user_id=user_id)
    except Exception:
        profile_markdown = ""

    return {
        "node": node,
        "path": path,
        "tutorials": tutorials,
        "current_tutorial": current_tutorial,
        "profile_markdown": profile_markdown,
    }


async def node_generate_tutorial(state: LearnState) -> dict:
    """生成节点教程内容 — 调用 NodeLearningAgent。"""
    if state.get("error"):
        return {}
    agent = NodeLearningAgent()
    node = state["node"]
    path = state["path"]
    result = await agent.generate_tutorial(
        path_goal=path.goal,
        node_title=node.title,
        mastery_target="掌握该节点核心能力",
        tutorial_type=state.get("tutorial_type", "primary"),
        weak_knowledge_points=state.get("weak_knowledge_points", []),
        profile_markdown=state.get("profile_markdown", ""),
    )
    return {"tutorial_content": result["content_markdown"]}


async def node_persist_tutorial_and_mark(state: LearnState) -> dict:
    """持久化教程并标记为 current，更新节点状态为 in_progress。"""
    if state.get("error"):
        return {}
    session = state["session"]
    node = state["node"]
    path = state["path"]
    user_id = state["user_id"]
    tutorial_type = state.get("tutorial_type", "primary")

    prev_stmt = select(PathNodeTutorial).where(
        PathNodeTutorial.node_id == node.id,
        PathNodeTutorial.is_current.is_(True),
    )
    prev_current = (await session.exec(prev_stmt)).first()
    if prev_current is not None:
        prev_current.is_current = False

    existing = state.get("tutorials", [])
    tutorial = PathNodeTutorial(
        path_id=path.id,
        node_id=node.id,
        user_id=user_id,
        tutorial_type=tutorial_type,
        version_no=len(existing) + 1,
        based_on_tutorial_id=state.get("based_on_tutorial_id"),
        is_current=True,
        title=f"{node.title} - {tutorial_type}",
        summary=tutorial_type,
        content_markdown=state["tutorial_content"],
        knowledge_points=[node.title],
        weak_knowledge_points=state.get("weak_knowledge_points", []),
    )
    session.add(tutorial)
    await session.flush()

    node.current_tutorial_id = tutorial.id
    if node.status == "available":
        node.status = "in_progress"
    if node.started_at is None:
        node.started_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(tutorial)
    return {"tutorial": tutorial}


async def node_generate_questions(state: LearnState) -> dict:
    """生成测验题目 — 若无教程则先自动生成主教程。"""
    if state.get("error"):
        return {}
    node = state["node"]
    path = state["path"]
    current_tutorial = state.get("current_tutorial")

    if current_tutorial is None:
        agent = NodeLearningAgent()
        result = await agent.generate_tutorial(
            path_goal=path.goal,
            node_title=node.title,
            mastery_target="掌握该节点核心能力",
            tutorial_type="primary",
            weak_knowledge_points=[],
            profile_markdown=state.get("profile_markdown", ""),
        )
        session = state["session"]
        tutorial = PathNodeTutorial(
            path_id=path.id,
            node_id=node.id,
            user_id=state["user_id"],
            tutorial_type="primary",
            version_no=1,
            is_current=True,
            title=f"{node.title} - primary",
            summary="primary",
            content_markdown=result["content_markdown"],
            knowledge_points=[node.title],
            weak_knowledge_points=[],
        )
        session.add(tutorial)
        await session.flush()
        node.current_tutorial_id = tutorial.id
        if node.started_at is None:
            node.started_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(tutorial)
        current_tutorial = tutorial

    round_no = await _latest_round(state["session"], node.id) + 1
    agent = NodeLearningAgent()
    generated = await agent.generate_questions(
        path_goal=path.goal,
        node_title=node.title,
        mastery_target="掌握该节点核心能力",
        tutorial_title=current_tutorial.title,
        tutorial_summary=current_tutorial.summary or current_tutorial.title,
        round_no=round_no,
    )
    if len(generated) != PATH_QUIZ_SIZE:
        return {"error": "当前节点还没有生成完整的五道题，请稍后重试"}
    return {"generated_questions": generated, "round_no": round_no}


async def node_persist_questions(state: LearnState) -> dict:
    """持久化测验题目到数据库。"""
    if state.get("error"):
        return {}
    session = state["session"]
    node = state["node"]
    path = state["path"]
    user_id = state["user_id"]
    current_tutorial = state.get("current_tutorial")
    round_no = state["round_no"]

    questions: list[PathNodeQuestion] = []
    for index, item in enumerate(
        state["generated_questions"][:PATH_QUIZ_SIZE], start=1
    ):
        question = PathNodeQuestion(
            path_id=path.id,
            node_id=node.id,
            tutorial_id=current_tutorial.id if current_tutorial else None,
            user_id=user_id,
            round_no=round_no,
            question_no=index,
            mode="quiz",
            type=item.get("type", "single_choice"),
            question=item["question"],
            choice=item.get("choice") or item.get("options") or {},
            answer=str(item["answer"]),
            analysis=item.get("analysis") or item.get("explanation"),
            knowledge_points=item.get("knowledge_points") or [],
        )
        session.add(question)
        questions.append(question)
    await session.commit()
    for q in questions:
        await session.refresh(q)
    return {"quiz_questions": questions}


async def node_score_answers(state: LearnState) -> dict:
    """评分用户答案，计算得分和薄弱知识点。"""
    if state.get("error"):
        return {}
    questions = state.get("quiz_questions", [])
    if len(questions) != PATH_QUIZ_SIZE:
        return {"error": "当前节点还没有完整的五道题"}
    answers = state.get("quiz_answers", [])
    answer_map = {item["question_id"]: item["response"] for item in answers}

    score = 0
    weak_points: list[str] = []
    for question in questions:
        response = answer_map.get(question.id)
        is_correct = response == question.answer
        question.response = response
        question.is_correct = is_correct
        question.submitted_at = datetime.now(timezone.utc)
        question.updated_at = question.submitted_at
        if is_correct:
            score += 1
        else:
            for point in question.knowledge_points or []:
                if point not in weak_points:
                    weak_points.append(point)
    return {
        "score": score,
        "passed": score >= PATH_PASS_SCORE,
        "weak_knowledge_points": weak_points,
    }


async def node_advance_state(state: LearnState) -> dict:
    """推进节点状态：completed/remediation/completed_with_gaps。"""
    if state.get("error"):
        return {}
    session = state["session"]
    node = state["node"]
    passed = state["passed"]
    weak_points = state.get("weak_knowledge_points", [])

    node.attempt_count += 1

    if passed:
        node.status = "completed"
        node.completed_at = datetime.now(timezone.utc)
        outcome = "completed"
    elif node.attempt_count == 1:
        node.status = "remediation"
        outcome = "remediation"
    elif node.attempt_count == 2:
        node.status = "completed_with_gaps"
        node.completed_at = datetime.now(timezone.utc)
        outcome = "completed_with_gaps"
    else:
        node.status = "completed_with_gaps"
        node.completed_at = datetime.now(timezone.utc)
        outcome = "completed_with_gaps"

    await session.commit()

    if outcome in ("completed", "completed_with_gaps"):
        try:
            from app.path.events import record_node_completed_event

            path = state["path"]
            await record_node_completed_event(
                db=session,
                user_id=state["user_id"],
                path_id=path.id,
                path_node_id=node.id,
                node_id=node.node_id,
                course=path.title,
                topic=node.title,
                score=float(state.get("score", 0) / PATH_QUIZ_SIZE * 100),
                weak_knowledge_points=(
                    weak_points if outcome == "completed_with_gaps" else None
                ),
            )
        except Exception:
            pass

    result: dict = {"outcome": outcome}
    if outcome == "remediation":
        result["tutorial_type"] = "remediation"
        result["weak_knowledge_points"] = weak_points
    elif outcome == "completed_with_gaps" and node.attempt_count == 2:
        primary = await _primary_tutorial(session, node.id)
        result["tutorial_type"] = "reinforced"
        result["weak_knowledge_points"] = weak_points
        result["based_on_tutorial_id"] = primary.id if primary else None
    return result


async def node_unlock_and_update_progress(state: LearnState) -> dict:
    """解锁后续节点并更新路径进度百分比。"""
    if state.get("error"):
        return {}
    session = state["session"]
    path = state["path"]

    nodes = await _path_nodes(session, path.id)
    completed = {n.node_id for n in nodes if n.status in COMPLETED_NODE_STATUSES}

    for n in nodes:
        if n.status == "locked" and set(n.prerequisites or []).issubset(completed):
            n.status = "available"

    if nodes:
        completed_count = sum(
            1 for n in nodes if n.status in COMPLETED_NODE_STATUSES
        )
        path.overall_progress = round(completed_count / len(nodes) * 100)
        next_node = next(
            (n for n in nodes if n.status in ACTIVE_NODE_STATUSES), None
        )
        path.current_node_key = next_node.node_id if next_node else None
        if completed_count == len(nodes):
            path.status = "completed"
        path.updated_at = datetime.now(timezone.utc)

    await session.commit()

    next_node = next(
        (n for n in nodes if n.status in ACTIVE_NODE_STATUSES), None
    )
    return {"next_node_id": next_node.id if next_node else None}


async def node_record_quiz_event(state: LearnState) -> dict:
    """记录测验事件到评估系统，触发画像更新。"""
    if state.get("error"):
        return {}
    session = state["session"]
    user_id = state["user_id"]
    node = state["node"]
    path = state["path"]

    outcome = state.get("outcome", "completed")
    score = state.get("score", 0)
    weak_points = state.get("weak_knowledge_points", [])

    from app.path.events import record_path_quiz_answered_event

    await record_path_quiz_answered_event(
        db=session,
        user_id=user_id,
        path_id=path.id,
        path_node_id=node.id,
        node_id=node.node_id,
        course=path.title,
        topic=node.title,
        score=float(score / PATH_QUIZ_SIZE * 100),
        outcome=outcome,
        weak_knowledge_points=weak_points,
    )

    return {}


async def node_generate_resource(state: LearnState) -> dict:
    """生成节点辅助资源 — 通过 path_helpers 调用 resource 模块 agent。"""
    if state.get("error"):
        return {}
    session = state["session"]
    node = state["node"]
    path = state["path"]
    resource_type = state.get("resource_type", "content")
    current_tutorial = state.get("current_tutorial")

    if current_tutorial is None:
        agent = NodeLearningAgent()
        result = await agent.generate_tutorial(
            path_goal=path.goal,
            node_title=node.title,
            mastery_target="掌握该节点核心能力",
            tutorial_type="primary",
            weak_knowledge_points=[],
            profile_markdown=state.get("profile_markdown", ""),
        )
        tutorial = PathNodeTutorial(
            path_id=path.id,
            node_id=node.id,
            user_id=state["user_id"],
            tutorial_type="primary",
            version_no=1,
            is_current=True,
            title=f"{node.title} - primary",
            summary="primary",
            content_markdown=result["content_markdown"],
            knowledge_points=[node.title],
            weak_knowledge_points=[],
        )
        session.add(tutorial)
        await session.flush()
        node.current_tutorial_id = tutorial.id
        if node.started_at is None:
            node.started_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(tutorial)
        current_tutorial = tutorial

    node_input = NodeInput(
        path_id=path.id,
        node_id=node.id,
        node_key=node.node_id,
        stage_id=node.stage_id,
        path_title=path.title,
        path_goal=path.goal,
        node_title=node.title,
        difficulty=node.difficulty,
        mastery_target=None,
        knowledge_points=list(current_tutorial.knowledge_points or []),
        weak_knowledge_points=list(current_tutorial.weak_knowledge_points or []),
        generation_focus=[],
        tutorial_title=current_tutorial.title,
        tutorial_summary=current_tutorial.summary,
        tutorial_markdown=current_tutorial.content_markdown,
        profile={},
        agent_config={},
        username="",
    )
    result = await generate_path_node_resource(resource_type, node_input)
    return {"resource_result": result, "resource_type": resource_type}


async def node_persist_resource(state: LearnState) -> dict:
    """持久化辅助资源到 PathNodeResource 表。"""
    if state.get("error"):
        return {}
    session = state["session"]
    node = state["node"]
    path = state["path"]
    user_id = state["user_id"]
    current_tutorial = state.get("current_tutorial")
    resource_type = state.get("resource_type", "content")
    result = state["resource_result"]

    existing_count = await _count_resources(session, node.id, resource_type)
    version_no = existing_count + 1
    title = (
        result.title
        if hasattr(result, "title") and result.title
        else f"{node.title} - {resource_type}"
    )

    if hasattr(result, "success") and not result.success:
        resource = PathNodeResource(
            path_id=path.id,
            node_id=node.id,
            tutorial_id=current_tutorial.id if current_tutorial else None,
            user_id=user_id,
            resource_type=resource_type,
            version_no=version_no,
            title=title,
            content_format="markdown",
            status="failed",
            error_message=(
                result.error if hasattr(result, "error") else "unknown"
            ),
            summary=result.summary if hasattr(result, "summary") else None,
            metadata_json=(
                result.metadata if hasattr(result, "metadata") else None
            ),
        )
        session.add(resource)
        await session.commit()
        await session.refresh(resource)
        return {"resource_dto": _resource_to_dict(resource)}

    content_text = None
    content_json_val = None
    file_type = getattr(result, "file_type", "markdown")
    raw_content = getattr(result, "content", "")
    if file_type == "json":
        try:
            content_json_val = (
                json.loads(raw_content)
                if isinstance(raw_content, str)
                else raw_content
            )
        except (json.JSONDecodeError, TypeError):
            content_text = str(raw_content)
    else:
        content_text = str(raw_content)

    resource = PathNodeResource(
        path_id=path.id,
        node_id=node.id,
        tutorial_id=current_tutorial.id if current_tutorial else None,
        user_id=user_id,
        resource_type=resource_type,
        version_no=version_no,
        title=title,
        content_format=file_type,
        content_text=content_text,
        content_json=content_json_val,
        summary=result.summary if hasattr(result, "summary") else None,
        status="completed",
        metadata_json=result.metadata if hasattr(result, "metadata") else None,
    )
    session.add(resource)
    await session.commit()
    await session.refresh(resource)
    return {"resource_dto": _resource_to_dict(resource)}


# ── 内部辅助函数 ──────────────────────────────────────────────────────────

async def _latest_round(session, node_id: int) -> int:
    stmt = select(PathNodeQuestion).where(PathNodeQuestion.node_id == node_id)
    questions = list((await session.exec(stmt)).all())
    return max((q.round_no for q in questions), default=0)


async def _primary_tutorial(session, node_id: int) -> PathNodeTutorial | None:
    stmt = (
        select(PathNodeTutorial)
        .where(
            PathNodeTutorial.node_id == node_id,
            PathNodeTutorial.tutorial_type == "primary",
        )
        .order_by(col(PathNodeTutorial.version_no).asc())
    )
    return (await session.exec(stmt)).first()


async def _path_nodes(session, path_id: int) -> list[PathNode]:
    stmt = (
        select(PathNode)
        .where(PathNode.path_id == path_id)
        .order_by(col(PathNode.priority).asc(), col(PathNode.id).asc())
    )
    return list((await session.exec(stmt)).all())


async def _count_resources(session, node_id: int, resource_type: str) -> int:
    stmt = select(PathNodeResource).where(
        PathNodeResource.node_id == node_id,
        PathNodeResource.resource_type == resource_type,
    )
    return len(list((await session.exec(stmt)).all()))


def _resource_to_dict(resource) -> dict:
    return {
        "id": resource.id,
        "resource_type": resource.resource_type,
        "version_no": resource.version_no,
        "title": resource.title,
        "content_format": resource.content_format,
        "content_text": resource.content_text,
        "content_json": resource.content_json,
        "summary": resource.summary,
        "status": resource.status or "completed",
        "error_message": resource.error_message,
        "created_at": (
            resource.created_at.isoformat() if resource.created_at else ""
        ),
    }


__all__ = [
    "NodeLearningAgent",
    "PathPlannerAgent",
    "get_learn_workflow",
    "repair_plan",
    "build_fallback_plan",
    "COMPLETED_NODE_STATUSES",
    "ACTIVE_NODE_STATUSES",
]
