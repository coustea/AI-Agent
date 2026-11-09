"""主规划智能体 (PlanAgent) — 负责学习目标拆解与任务拓扑图编排 (app.resource.agents.planner)。

在 Plan-and-Execute 架构中充当核心主脑，将统一的学习请求拆解为包含依赖关系、
执行角色与工具声明的 TaskNode 列表。
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from app.infra.llm import LLM
from app.resource.schemas import ExecutionPlan, TaskNode, TaskStatus

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, int], Awaitable[None]]

_ROLE_MAP: dict[str, str] = {
    "content": "资深课程讲师",
    "mindmap": "知识体系架构师",
    "quiz": "教学测评出题专家",
    "code": "资深软件研发专家",
    "reading": "学科文献策展人",
    "ppt": "课件视觉设计专家",
    "cartoon": "数字教学动画编导",
}

_TOOL_MAP: dict[str, str] = {
    "ppt": "generate_ppt_deck",
    "cartoon": "generate_teaching_video",
}


class PlanAgent:
    """主规划智能体：负责分析学习需求、目标及难度，规划并产出执行拓扑图 (ExecutionPlan)。"""

    agent_id = "planning"
    agent_name = "认知规划主智能体"

    def __init__(self) -> None:
        """初始化规划智能体并创建结构化决策 LLM 实例。"""
        self.llm = LLM(temperature=0.2)

    async def plan(
        self,
        *,
        topic: str,
        learning_goal: str = "",
        target_resources: list[str],
        difficulty: str = "intermediate",
        preferences: dict[str, Any] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> ExecutionPlan:
        """分析学习主题与需求，动态生成带拓扑依赖的 ExecutionPlan。"""
        logger.info("PlanAgent 开始规划: topic=%s targets=%s", topic, target_resources)
        if progress_callback:
            await progress_callback("正在深入解析学习目标与知识脉络...", 30)

        # 整理默认交付物清单
        valid_targets = [r for r in target_resources if r]
        if not valid_targets:
            valid_targets = ["content", "mindmap", "quiz"]

        prompt = self._build_prompt(
            topic=topic,
            learning_goal=learning_goal,
            target_resources=valid_targets,
            difficulty=difficulty,
            preferences=preferences or {},
        )

        try:
            plan = await self.llm.json(ExecutionPlan, prompt)
            self._ensure_all_targets_covered(plan, valid_targets, topic)
            if progress_callback:
                await progress_callback("执行拓扑图规划构建完成", 100)
            return plan
        except Exception as exc:
            logger.warning("大模型生成规划异常，启用规则兜底构建 Plan: %s", exc)
            fallback = self._build_fallback_plan(
                topic=topic,
                learning_goal=learning_goal,
                target_resources=valid_targets,
                difficulty=difficulty,
            )
            if progress_callback:
                await progress_callback("默认执行拓扑图构建就绪", 100)
            return fallback

    def _build_prompt(
        self,
        *,
        topic: str,
        learning_goal: str,
        target_resources: list[str],
        difficulty: str,
        preferences: dict[str, Any],
    ) -> str:
        """构建要求大模型产出结构化 DAG 任务图的 System Prompt。"""
        return f"""你是一位世界顶尖的教学架构与认知科学规划专家。
你的任务是将用户的学习需求规划为一份结构严密、支持并发执行的教学资源生成拓扑图 (ExecutionPlan)。

【学习需求信息】
- 主题 (Topic): {topic}
- 学习目标 (Goal): {learning_goal or "掌握核心概念、内在机理及实际应用方法"}
- 难度级别 (Difficulty): {difficulty} (beginner: 初学入门 / intermediate: 进阶实操 / advanced: 深度源码与架构)
- 交付资源清单: {", ".join(target_resources)}
- 补充偏好: {preferences}

【拓扑规划规则】
1. 若交付物中包含 'content' (概念精讲)，通常作为无依赖的基础先行任务 (dependencies: [])。
2. 若包含多模态资源：
   - 'ppt' (演示课件)：task_type 必须为 'tool'，tool_name 必须为 'generate_ppt_deck'。如果存在 content，则 dependencies 设为 ['content']。
   - 'cartoon' (教学动画)：task_type 必须为 'tool'，tool_name 必须为 'generate_teaching_video'。如果存在 content，则 dependencies 设为 ['content']。
3. 文本类资源 ('content', 'mindmap', 'quiz', 'code', 'reading')：
   - task_type 必须为 'text'，tool_name 为 null。
   - 'mindmap'、'quiz'、'code'、'reading' 若存在 'content'，通常依赖 ['content']，以便从精讲讲义中提取核心概念。
4. 为每个 TaskNode 设置清晰的角色 (subagent_role) 和专门的指导要求 (task_prompt)。

请严格按照 JSON Schema 输出 ExecutionPlan，必须覆盖所有交付资源清单！
"""

    def _ensure_all_targets_covered(
        self,
        plan: ExecutionPlan,
        target_resources: list[str],
        topic: str,
    ) -> None:
        """确保规划结果覆盖了全部请求的目标资源类型。"""
        existing_types = {t.resource_type for t in plan.tasks}
        has_content = "content" in existing_types or "content" in target_resources

        for res_type in target_resources:
            if res_type in existing_types:
                continue
            is_tool = res_type in _TOOL_MAP
            deps = ["content"] if has_content and res_type != "content" else []
            plan.tasks.append(
                TaskNode(
                    task_id=res_type,
                    title=f"{topic} - {_ROLE_MAP.get(res_type, res_type)}",
                    resource_type=res_type,
                    task_type="tool" if is_tool else "text",
                    tool_name=_TOOL_MAP.get(res_type),
                    dependencies=deps,
                    subagent_role=_ROLE_MAP.get(res_type, "学科专家"),
                    task_prompt=f"围绕主题 {topic} 高质量完成 {res_type} 生成任务",
                    status=TaskStatus.PENDING,
                )
            )

    def _build_fallback_plan(
        self,
        *,
        topic: str,
        learning_goal: str,
        target_resources: list[str],
        difficulty: str,
    ) -> ExecutionPlan:
        """规则兜底：当大模型规划异常时，基于教学依赖关系生成确定性的标准 DAG。"""
        tasks: list[TaskNode] = []
        has_content = "content" in target_resources

        for res_type in target_resources:
            is_tool = res_type in _TOOL_MAP
            deps = ["content"] if (has_content and res_type != "content") else []
            tasks.append(
                TaskNode(
                    task_id=res_type,
                    title=f"{topic} {_ROLE_MAP.get(res_type, res_type).split('—')[0].strip()}",
                    resource_type=res_type,
                    task_type="tool" if is_tool else "text",
                    tool_name=_TOOL_MAP.get(res_type),
                    dependencies=deps,
                    subagent_role=_ROLE_MAP.get(res_type, "学科专家"),
                    task_prompt=f"针对 {difficulty} 难度，围绕 {topic} 生成高水准 {res_type} 教学资源",
                    status=TaskStatus.PENDING,
                )
            )

        return ExecutionPlan(
            topic=topic,
            learning_goal=learning_goal or f"深入掌握 {topic}",
            difficulty=difficulty,  # type: ignore[arg-type]
            overview=f"系统化学习方案：结合理论精讲、结构可视化、实践检测与多媒体手段全方位掌握 {topic}。",
            tasks=tasks,
        )

    async def generate_resource(self, *args: Any, **kwargs: Any) -> Any:
        """兼容生成执行入口。"""
        return await self.plan(*args, **kwargs)


# 兼容别名
PlannerAgent = PlanAgent
PlanningAgent = PlanAgent
