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
import re
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
    User,
    WrongQuestion,
)
from app.profile.service import get_profile_service
from app.resource.schemas import AgentResult
from app.rag.tools import build_knowledge_tool
from app.shared.research import ResearchAgent, ResearchTask

# 从本地合并后的 schemas 导入
from app.path.schemas import (
    LearningPlan,
    PlanNode,
    AgentStage,
    PathRequest,
    PathPreferences,
    LearnState,
    AgentQuestionSet,
    LearningPathTutorialDTO,
)

logger = get_logger(__name__)

# ======================================================================
# 偏好参数语义化映射
# ======================================================================

# 学习场景 → 自然语言描述
SCENE_DESCRIPTIONS: dict[str, str] = {
    "general": "通用学习场景，注重知识体系完整性和循序渐进",
    "exam": "考试复习场景，重点覆盖高频考点和易错点，强化记忆和练习",
    "beginner": "基础入门场景，从零开始讲解，强调概念清晰和示例丰富",
    "project": "项目实战场景，以实际项目为主线，边做边学，强调动手实践",
    "interview": "面试准备场景，聚焦高频面试题和核心概念，强调表达和总结",
}

# 学习节奏 → 自然语言描述
PACE_DESCRIPTIONS: dict[str, str] = {
    "slow": "慢速细学，每个知识点展开讲解，提供更多背景知识和延伸阅读",
    "normal": "正常节奏，平衡讲解深度和推进速度",
    "fast": "快速推进，精简内容，聚焦核心要点，减少冗余讲解",
}

# 路径粒度 → 自然语言描述
GRANULARITY_DESCRIPTIONS: dict[str, str] = {
    "coarse": "粗略路径，阶段和节点数量较少（建议3-5个阶段，每阶段2-3个节点）",
    "standard": "标准路径，阶段和节点数量适中（建议4-6个阶段，每阶段3-5个节点）",
    "fine": "细节点路径，阶段和节点数量较多（建议5-8个阶段，每阶段4-6个节点）",
}

# 规划重点 → 自然语言描述
FOCUS_DESCRIPTIONS: dict[str, str] = {
    "foundation": "补基础：优先安排基础概念和前置知识，确保根基稳固",
    "key_points": "抓重点：聚焦核心考点和关键机制，减少边缘内容",
    "practice": "多练习：增加练习题和实战环节，强化动手能力",
    "weakness": "补薄弱点：针对已知薄弱环节强化，重点攻克易错点",
}

# ======================================================================
# 1. 兜底与修复规划函数
# ======================================================================

# 修复 LLM 生成的路径规划，确保 stages 和 nodes 正确对齐
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


# 构建兜底学习路径（当 LLM 规划失败时使用）
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
# 1.5 Markdown 元数据标题块解析工具
# ======================================================================


# 从 LLM 生成的 Markdown 中提取元数据标题块
def _parse_markdown_metadata(text: str) -> tuple[dict, str]:
    """从 LLM 生成的 Markdown 中提取元数据标题块。

    期望格式：
    ```
    # 教程标题

    > **摘要**：一句话摘要
    >
    > **知识点**：知识点1、知识点2
    >
    > **类型**：primary

    ## 1. 正文...
    ```

    Returns:
        (metadata_dict, body_text) — 无法解析时返回 ({}, text)。
    """
    stripped = text.lstrip()
    meta: dict = {}

    # 1. 提取一级标题作为 title
    title_match = re.match(r"^#\s+(.+?)\s*\n", stripped)
    if not title_match:
        return {}, text

    meta["title"] = title_match.group(1).strip()
    rest = stripped[title_match.end():]

    # 2. 提取 blockquote 中的元数据字段
    bq_lines: list[str] = []
    for line in rest.split("\n"):
        stripped_line = line.strip()
        if stripped_line.startswith(">"):
            bq_lines.append(stripped_line[1:].strip())
        elif stripped_line == "" and bq_lines:
            continue
        else:
            break

    bq_text = " ".join(bq_lines)

    # 提取摘要
    summary_match = re.search(r"\*\*摘要\*\*[：:]\s*(.+?)(?=\s*\*\*|$)", bq_text)
    if summary_match:
        meta["summary"] = summary_match.group(1).strip()

    # 提取知识点
    kp_match = re.search(r"\*\*知识点\*\*[：:]\s*(.+?)(?=\s*\*\*|$)", bq_text)
    if kp_match:
        kp_raw = kp_match.group(1).strip()
        meta["knowledge_points"] = [
            k.strip() for k in re.split(r"[、,，;；]", kp_raw) if k.strip()
        ]

    # 提取类型
    type_match = re.search(r"\*\*类型\*\*[：:]\s*(\w+)", bq_text)
    if type_match:
        meta["type"] = type_match.group(1).strip()

    # 3. 找到正文起始位置（第一个 ## 标题）
    body_match = re.search(r"\n##\s", rest)
    if body_match:
        body = rest[body_match.start() + 1:]
    else:
        body = rest

    return meta, body


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
    guidance_strategy: dict[str, Any]


# 路径规划智能体：联网检索 + LLM 生成阶段与节点
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

    # 构建规划工作流状态图：research → strategist
    def _build_graph(self):
        workflow = StateGraph(PathState)

        # research 节点：联网检索课程结构参考资料
        async def research_node(state: PathState) -> dict[str, Any]:
            loguru_logger.info("LangGraph [Path Research] 开始...")
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
                "LangGraph [Path Research] 完成, 上下文长度=%d",
                len(search_context),
            )
            return {"search_context": search_context}

        # strategist 节点：基于画像、目标与检索结果生成阶段与节点
        async def node_strategist_node(state: PathState) -> dict[str, Any]:
            loguru_logger.info("LangGraph [Node Strategist] 开始...")
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

            # 根据用户偏好决定是否融合个人画像
            use_profile = state["request"].preferences.use_profile
            if not use_profile:
                profile_md = ""
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

            # 调用 LLM 生成结构化学习计划
            result = await self.llm.ainvoke_json(
                LearningPlan,
                messages,
                max_tokens=4096,
            )

            # 修复对齐 stages 与 nodes
            result = repair_plan(
                plan=result,
                macro_stages=result.stages,
                request=state["request"],
            )
            loguru_logger.info(
                "LangGraph [Node Strategist] 完成, 节点数=%d",
                len(result.nodes),
            )
            return {"final_plan": result}

        # 注册节点与边，编译状态图
        workflow.add_node("research", research_node)
        workflow.add_node("strategist", node_strategist_node)
        workflow.add_edge(START, "research")
        workflow.add_edge("research", "strategist")
        workflow.add_edge("strategist", END)

        return workflow.compile()

    async def generate_plan(self, request: PathRequest, profile: dict[str, Any], progress_callback: ProgressCallback | None = None, profile_markdown: str = "", guidance_strategy: dict[str, Any] = None) -> LearningPlan:
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
                "guidance_strategy": guidance_strategy or {},
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

    # 将搜索结果格式化为纯文本上下文
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

    # 联网检索课程结构参考，返回格式化上下文
    async def _search(
        self,
        request: PathRequest,
        profile: dict[str, Any],
    ) -> str:

        try:
            # 构造检索任务并执行
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
                "[PathPlannerAgent] ResearchAgent 检索失败: %s", exc
            )
            return ""


# 组装路径规划的 system + human 消息
def _build_planner_messages(
    *,
    request_context: str,
    search_context: str,
    profile_markdown: str,
) -> list[Any]:
    """组装路径规划的 LLM 消息。

    消息结构：
    - System: 规划系统提示（从 prompts 读取）
    - Human: 结构化的请求上下文 + 画像 + 检索参考
    """
    sys_msg = SystemMessage(
        content=prompts.get("path").get("planner_system")
    )

    # 构建画像融合提示
    profile_section = ""
    if profile_markdown:
        profile_section = (
            "\n\n## 学习者画像\n\n"
            "以下是学习者的个人画像，请结合画像特点进行个性化规划：\n\n"
            f"{profile_markdown}"
        )

    # 构建检索参考提示
    search_section = ""
    if search_context:
        search_section = f"\n\n## 联网参考\n\n{search_context}"

    human_msg = HumanMessage(
        content=(
            "请根据以下信息生成学习路径 JSON。\n\n"
            f"## 学习请求\n\n{request_context}"
            f"{profile_section}"
            f"{search_section}"
            "\n\n再次强调：只输出符合 schema 的 JSON 根对象，不要输出 Markdown，不要输出解释文字。"
        )
    )
    return [sys_msg, human_msg]


# 将 PathRequest 格式化为可读的请求上下文文本
def _format_request(request: PathRequest) -> str:
    """格式化请求参数为可读文本，供 LLM prompt 使用。

    将结构化的偏好参数转换为自然语言描述，让 LLM 更好理解用户意图。
    """
    current_knowledge = (
        "、".join(request.current_knowledge)
        if request.current_knowledge
        else "未提供"
    )

    # 语义化偏好参数
    preferences_desc = _format_preferences(request.preferences)

    return (
        f"学习目标: {request.goal}\n"
        f"学习主题: {request.topic or '未提供'}\n"
        f"已掌握知识: {current_knowledge}\n"
        f"学习偏好:\n{preferences_desc}"
    )


# 将结构化偏好参数转换为自然语言描述
def _format_preferences(preferences: PathPreferences) -> str:
    """将结构化偏好参数转换为自然语言描述。"""
    lines: list[str] = []

    # 学习场景
    scene_desc = SCENE_DESCRIPTIONS.get(preferences.scene, "通用学习场景")
    lines.append(f"- 学习场景：{scene_desc}")

    # 学习节奏
    pace_desc = PACE_DESCRIPTIONS.get(preferences.pace, "正常节奏")
    lines.append(f"- 学习节奏：{pace_desc}")

    # 路径粒度
    granularity_desc = GRANULARITY_DESCRIPTIONS.get(preferences.granularity, "标准路径")
    lines.append(f"- 路径粒度：{granularity_desc}")

    # 规划重点
    if preferences.focus:
        focus_items = [FOCUS_DESCRIPTIONS.get(f, f) for f in preferences.focus]
        lines.append(f"- 规划重点：{'；'.join(focus_items)}")

    # 是否使用画像（在 prompt 中单独处理，此处仅备注）
    if not preferences.use_profile:
        lines.append("- 画像融合：用户已关闭画像融合，仅根据学习目标规划")

    return "\n".join(lines)



# 安全触发进度回调（回调为空时忽略）
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

# 节点学习智能体：调用 LLM 生成教程内容和测验题目
class NodeLearningAgent:
    """节点学习智能体 — 调用 LLM 生成节点教程内容和测验题目。

    主要方法：
    - generate_tutorial：生成教程 Markdown
    - generate_questions：生成 5 道测验题目
    """

    def __init__(self) -> None:
        self.llm = get_llm()

    # 生成节点教程 Markdown 内容（调用 LLM）
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
        # 拼装薄弱知识点强化说明
        weak_points_section = ""
        if weak_knowledge_points:
            weak_points_section = (
                f"重点围绕这些薄弱知识点强化：{', '.join(weak_knowledge_points)}"
            )
        profile_section = (
            f"学习者画像:\n{profile_markdown[:2000]}" if profile_markdown else ""
        )
        # 本地知识库检索 —— 直接调用 RAG 工具，为教程提供权威教材依据
        try:
            kb_result = await build_knowledge_tool().handler(query=node_title)
            kb_section = (
                kb_result.get("text")
                if isinstance(kb_result, dict) and kb_result.get("status") == "ok"
                else "无"
            )
        except Exception as exc:
            logger.warning("[NodeLearningAgent] 知识库检索失败: %s", exc)
            kb_section = "无"
        # 根据 tutorial_type 选择对应的 prompt
        prompt_key = "tutorial_primary"  # 简化：只生成主教程
        prompt = prompts.get("path").render(
            prompt_key,
            path_goal=path_goal,
            node_title=node_title,
            mastery_target=mastery_target,
            weak_points_section=weak_points_section,
            profile_section=profile_section,
            kb_section=kb_section,
        )
        response = await self.llm.ainvoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        return {
            "title": f"{node_title} - {tutorial_type}",
            "summary": tutorial_type,
            "content_markdown": content,
            "knowledge_points": [node_title],
        }

    # 生成 5 道测验题目并归一化为字典列表
    async def generate_questions(
        self,
        *,
        path_goal: str,
        node_title: str,
        mastery_target: str,
        tutorial_title: str,
        tutorial_summary: str,
        round_no: int,
        max_retries: int = 3,
    ) -> list[dict[str, Any]]:
        """生成测验题目，带重试机制确保返回 5 道题。"""
        prompt = prompts.get("path").render(
            "question_generation",
            path_goal=path_goal,
            node_title=node_title,
            mastery_target=mastery_target,
            tutorial_title=tutorial_title,
            tutorial_summary=tutorial_summary,
            round_no=round_no,
        )

        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                result = await self.llm.ainvoke_json(AgentQuestionSet, prompt)
                questions = result.questions if hasattr(result, "questions") else []
                if len(questions) == PATH_QUIZ_SIZE:
                    # 归一化每道题的字段结构
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
                    logger.info(
                        "[NodeLearningAgent] 成功生成 %d 道测验题 (attempt=%d)",
                        len(normalized), attempt + 1,
                    )
                    return normalized
                else:
                    logger.warning(
                        "[NodeLearningAgent] 题目数量不足: 期望 %d, 实际 %d (attempt=%d)",
                        PATH_QUIZ_SIZE, len(questions), attempt + 1,
                    )
            except Exception as e:
                last_error = e
                logger.warning(
                    "[NodeLearningAgent] 生成测验题失败 (attempt=%d): %s",
                    attempt + 1, e,
                )

        # 所有重试都失败
        logger.error(
            "[NodeLearningAgent] 生成测验题最终失败，已重试 %d 次: %s",
            max_retries, last_error,
        )
        return []


# ======================================================================
# 4. 节点学习工作流
# ======================================================================

# 节点完成状态集合
COMPLETED_NODE_STATUSES = frozenset({"completed", "completed_with_gaps"})

# 节点活跃状态集合（简化：移除 remediation 和 reinforced）
ACTIVE_NODE_STATUSES = frozenset({"available", "in_progress"})


# 工作流路由函数：根据 phase 字段决定下一个节点
def _route_by_phase(state: LearnState) -> str:
    """路由函数：根据 phase 字段决定下一个节点。"""
    return state["phase"]


# 工作流路由函数：根据测验结果决定下一步（直接解锁）
def _route_by_outcome(state: LearnState) -> str:
    """路由函数：根据测验结果决定下一步（简化流程：直接解锁后续节点）。"""
    return "unlock_progress"


# 构建节点学习 LangGraph 工作流（教程 → 测验 → 资源）
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
    wf.add_node("record_event", node_record_quiz_event)

    wf.add_edge(START, "load_context")

    wf.add_conditional_edges(
        "load_context",
        _route_by_phase,
        {
            "start": "gen_primary_tutorial",
            "questions": "gen_questions",
            "quiz": "score_answers",
        },
    )

    wf.add_edge("gen_primary_tutorial", "persist_tutorial_start")
    wf.add_edge("persist_tutorial_start", END)

    wf.add_edge("gen_questions", "persist_questions")
    wf.add_edge("persist_questions", END)

    wf.add_edge("score_answers", "advance_state")
    wf.add_edge("advance_state", "unlock_progress")

    wf.add_edge("unlock_progress", "record_event")

    return wf.compile()


_learn_workflow: StateGraph | None = None


# 获取节点学习工作流编译后状态图（单例）
def get_learn_workflow() -> StateGraph:
    """获取节点学习工作流的编译后状态图（单例）。"""
    global _learn_workflow
    if _learn_workflow is None:
        _learn_workflow = _build_learn_workflow()
    return _learn_workflow


# ── 工作流节点函数 ──────────────────────────────────────────────────────────

# 工作流节点：加载节点上下文（PathNode、教程、画像）
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

    user = await session.get(User, user_id)
    username = user.username if user is not None else ""

    return {
        "node": node,
        "path": path,
        "tutorials": tutorials,
        "current_tutorial": current_tutorial,
        "profile_markdown": profile_markdown,
        "username": username,
    }


# 工作流节点：生成节点教程内容
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


# 工作流节点：持久化教程并标记为 current
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
    content_md = state["tutorial_content"]
    meta, body = _parse_markdown_metadata(content_md)

    if meta.get("type") and meta["type"] != tutorial_type:
        logger.warning(
            "Tutorial type mismatch: LLM output type=%r, expected type=%r for node=%s",
            meta["type"], tutorial_type, node.title,
        )

    tutorial = PathNodeTutorial(
        path_id=path.id,
        node_id=node.id,
        user_id=user_id,
        tutorial_type=tutorial_type,
        version_no=len(existing) + 1,
        based_on_tutorial_id=state.get("based_on_tutorial_id"),
        is_current=True,
        title=meta.get("title", f"{node.title} - {tutorial_type}"),
        summary=meta.get("summary", tutorial_type),
        content_markdown=body,
        knowledge_points=meta.get("knowledge_points", [node.title]),
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


# 工作流节点：生成测验题目（需要先有教程）
async def node_generate_questions(state: LearnState) -> dict:
    """生成测验题目 — 需要先有教程，不自创建。"""
    if state.get("error"):
        return {}
    node = state["node"]
    path = state["path"]
    current_tutorial = state.get("current_tutorial")

    if current_tutorial is None:
        return {"error": "当前节点还没有教程，请先生成主教程再生成测验"}

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


# 工作流节点：持久化测验题目到数据库
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


# 工作流节点：评分用户答案，计算得分和薄弱知识点
async def node_score_answers(state: LearnState) -> dict:
    """评分用户答案，计算得分和薄弱知识点，并将错题写入错题本。"""
    if state.get("error"):
        return {}
    session = state["session"]
    questions = state.get("quiz_questions", [])
    if len(questions) != PATH_QUIZ_SIZE:
        return {"error": "当前节点还没有完整的五道题"}
    if any(question.submitted_at is not None for question in questions):
        return {"error": "当前轮次已经提交，不能重复提交"}
    answers = state.get("quiz_answers", [])
    submitted_ids = [item["question_id"] for item in answers]
    expected_ids = {question.id for question in questions}
    if len(set(submitted_ids)) != len(submitted_ids) or set(submitted_ids) != expected_ids:
        return {"error": "提交答案必须对应当前轮次的全部题目"}
    if any(not str(item.get("response", "")).strip() for item in answers):
        return {"error": "答案不能为空"}
    answer_map = {item["question_id"]: item["response"] for item in answers}

    node = state["node"]
    path = state["path"]

    # 逐题比对答案，累计得分并收集错题知识点
    score = 0
    weak_points: list[str] = []
    wrong_questions: list[dict] = []  # 收集错题信息用于写入错题本
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
            # 收集错题信息
            wrong_questions.append({
                "question_id": f"path-{path.id}-{node.node_id}-{question.id}",
                "subject": path.title,
                "question_type": question.type or "single_choice",
                "content": question.question,
                "options_json": question.choice or {},
                "standard_answer": question.answer,
                "analysis": question.analysis,
                "user_answer": response,
                "knowledge_points": question.knowledge_points or [],
            })

    # 将错题写入错题本
    if wrong_questions:
        await _save_wrong_questions(
            session=session,
            user_id=state["user_id"],
            wrong_questions=wrong_questions,
        )

    return {
        "score": score,
        "passed": score >= PATH_PASS_SCORE,
        "weak_knowledge_points": weak_points,
    }


# 工作流节点：推进节点状态（简化流程：一次测验即完成）
async def node_advance_state(state: LearnState) -> dict:
    """推进节点状态：completed/completed_with_gaps（简化：不再生成补救/强化教程）。"""
    if state.get("error"):
        return {}
    session = state["session"]
    node = state["node"]
    passed = state["passed"]
    weak_points = state.get("weak_knowledge_points", [])

    node.attempt_count += 1

    # 简化逻辑：测验后直接标记为完成（通过或有缺陷完成）
    if passed:
        node.status = "completed"
        node.completed_at = datetime.now(timezone.utc)
        outcome = "completed"
    else:
        node.status = "completed_with_gaps"
        node.completed_at = datetime.now(timezone.utc)
        outcome = "completed_with_gaps"

    await session.commit()

    # 记录学习事件
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

    return {
        "outcome": outcome,
        "weak_knowledge_points": weak_points if outcome == "completed_with_gaps" else [],
    }


# 工作流节点：解锁后续节点并更新路径进度百分比
async def node_unlock_and_update_progress(state: LearnState) -> dict:
    """解锁后续节点并更新路径进度百分比。"""
    if state.get("error"):
        return {}
    session = state["session"]
    path = state["path"]

    nodes = await _path_nodes(session, path.id)
    completed = {n.node_id for n in nodes if n.status in COMPLETED_NODE_STATUSES}

    # 前置全部完成的锁定节点解锁为可用
    for n in nodes:
        if n.status == "locked" and set(n.prerequisites or []).issubset(completed):
            n.status = "available"

    # 重算整体进度、当前节点与完成状态
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
            path.overall_progress = 100
            path.status = "completed"
        else:
            path.status = "active"
        path.updated_at = datetime.now(timezone.utc)

    await session.commit()

    next_node = next(
        (n for n in nodes if n.status in ACTIVE_NODE_STATUSES), None
    )
    return {"next_node_id": next_node.id if next_node else None}


# 工作流节点：记录测验事件到评估系统
async def node_record_quiz_event(state: LearnState) -> dict:
    """记录测验事件到评估系统。"""
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




# ── 内部辅助函数 ──────────────────────────────────────────────────────────

# 查询节点最新测验轮次编号
async def _latest_round(session, node_id: int) -> int:
    stmt = select(PathNodeQuestion).where(PathNodeQuestion.node_id == node_id)
    questions = list((await session.exec(stmt)).all())
    return max((q.round_no for q in questions), default=0)


# 获取节点的主教程（primary，最早版本）
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


# 按优先级获取路径的所有节点
async def _path_nodes(session, path_id: int) -> list[PathNode]:
    stmt = (
        select(PathNode)
        .where(PathNode.path_id == path_id)
        .order_by(col(PathNode.priority).asc(), col(PathNode.id).asc())
    )
    return list((await session.exec(stmt)).all())


# 统计节点指定类型的资源数量（用于计算版本号）
async def _count_resources(session, node_id: int, resource_type: str) -> int:
    stmt = select(PathNodeResource).where(
        PathNodeResource.node_id == node_id,
        PathNodeResource.resource_type == resource_type,
    )
    return len(list((await session.exec(stmt)).all()))


# 将 PathNodeResource 序列化为 DTO 字典
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


# 将路径测验错题写入错题本
async def _save_wrong_questions(
    session,
    user_id: int,
    wrong_questions: list[dict],
) -> None:
    """将路径测验错题写入错题本。

    对已存在的错题，累加错误次数并更新用户答案；
    对新错题，创建完整记录（包含题目快照）。
    """
    for item in wrong_questions:
        question_id = item["question_id"]

        # 查询该题是否已存在于错题本
        existing = (await session.exec(
            select(WrongQuestion).where(
                WrongQuestion.user_id == user_id,
                WrongQuestion.question_id == question_id,
            )
        )).scalars().first()

        if existing:
            # 已存在则累加错误次数并更新用户答案、取消归档
            existing.wrong_count += 1
            existing.user_answer = item["user_answer"]
            existing.is_archived = False
        else:
            # 创建新错题记录
            wrong = WrongQuestion(
                user_id=user_id,
                question_id=question_id,
                subject=item["subject"],
                question_type=item["question_type"],
                content=item["content"],
                options_json=item["options_json"],
                standard_answer=item["standard_answer"],
                analysis=item["analysis"],
                user_answer=item["user_answer"],
                wrong_count=1,
            )
            session.add(wrong)

    await session.flush()
    logger.info(
        "[PathWorkflows] 已将 %d 道错题写入错题本: user_id=%s",
        len(wrong_questions), user_id,
    )


__all__ = [
    "NodeLearningAgent",
    "PathPlannerAgent",
    "get_learn_workflow",
    "repair_plan",
    "build_fallback_plan",
    "COMPLETED_NODE_STATUSES",
    "ACTIVE_NODE_STATUSES",
]
