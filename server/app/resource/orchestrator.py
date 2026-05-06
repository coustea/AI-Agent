"""
资源生成编排器。

实现完整的资源生成工作流：
1. create_task - 创建任务记录
2. load_profile - 加载后端学习者画像
3. plan_workflow - MasterAgent 规划工作流
4. execute_layer - 分层执行各 Worker Agent
5. review_resources - ReviewerAgent 审查资源
6. assemble_bundle - AssemblerAgent 整合资源包
7. finalize - 完成
"""

from __future__ import annotations

import json
import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from langchain_core.messages import HumanMessage

from app.infra.logging import get_logger
from app.resource.events import AgentEventEmitter
from app.resource.registry import ensure_initialized, get_agent_entry
from app.resource.utils import load_profile_snapshot
from app.infra.llm import get_llm_manager
from app.shared.json_utils import parse_first_json_object
from app.resource.schemas import (
    AgentTask,
    AgentSelection,
    GeneratedResourceItem,
    LayerPlan,
    PlanningContext,
    ResourceBundle,
    ResourceGenerationRequest,
    ResourceAgentId,
    ReviewIssue,
    ReviewResult,
    StudyPathStep,
    WorkerState,
)
from app.resource.worker_agents import (
    CodeAgent,
    ContentAgent,
    DiagramAgent,
    MindmapAgent,
    QuizAgent,
    ReadingAgent,
)

logger = get_logger(__name__)


# Agent 间依赖关系图：key 为 agent_id，value 为前置依赖 agent_id 列表
AGENT_DEPENDENCIES: dict[str, list[str]] = {
    "content": [],         # 课程内容无依赖
    "mindmap": [],         # 思维导图无依赖
    "diagram": [],         # 知识图解无依赖
    "code": ["content"],   # 代码实操依赖课程内容
    "reading": ["content"],  # 拓展阅读依赖课程内容
    "quiz": ["content", "code"],  # 练习题依赖课程内容和代码
    "video": ["content", "diagram"],  # 视频依赖课程内容和图解
}

# 学习路径默认顺序（按 Layer 0 → Layer 1 → Layer 2 排列）
STUDY_PATH_ORDER = ["content", "mindmap", "diagram", "code", "quiz", "reading"]

# 学习路径预计时间（分钟），供前端展示学习规划时长
STUDY_PATH_ESTIMATED_TIME = {
    "content": 8,
    "diagram": 5,
    "mindmap": 5,
    "code": 12,
    "quiz": 15,
    "reading": 20,
}

# Agent 字符串标识到实现类的映射，用于运行时动态实例化 Worker Agent
AGENT_CLASS_MAP = {
    "content": ContentAgent,
    "mindmap": MindmapAgent,
    "diagram": DiagramAgent,
    "quiz": QuizAgent,
    "reading": ReadingAgent,
    "code": CodeAgent,
}


class MasterAgent:
    """MasterAgent：只负责当前层资源生成任务规划，不生成资源正文。"""

    # 三层学习架构：Layer 0 认知建构 → Layer 1 实践拓展 → Layer 2 检测巩固
    LAYER_AGENTS: dict[int, list[str]] = {
        0: ["content", "mindmap", "diagram"],
        1: ["code", "reading"],
        2: ["quiz"],
    }

    def __init__(self, llm: Any | None = None) -> None:
        # 允许外部注入 LLM 实例用于测试，否则使用 Spark Max 模型
        if llm is not None:
            self.llm = llm
        else:
            self.llm = get_llm_manager().get_model("spark_max")

    async def plan_layer(self, context: PlanningContext) -> LayerPlan:
        """使用 LLM 规划当前层；失败或非法时退回规则规划。"""

        # 获取当前层配置的候选 Agent 列表，再过滤出用户显式启用的 Agent
        layer = self.LAYER_AGENTS.get(context.layer, [])
        candidates = [a for a in layer if a in context.user_explicit_selection]
        explicit_set = set(context.user_explicit_selection)

        # 当前层无候选 Agent 时直接返回空规划，避免无效调用
        if not candidates:
            return LayerPlan(layer=context.layer, agents=[], reasoning="本层无待执行 Agent", fallback_used=False)

        try:
            # 优先尝试 LLM 智能规划，可根据上下文自适应选择 Agent 和参数
            raw_plan = await self._call_llm_for_layer(context=context, candidates=candidates)
            return self._sanitize_layer_plan(raw_plan, candidates, explicit_set, context)
        except Exception as exc:
            # LLM 规划失败（如模型超时、返回格式错误）时回退到规则兜底规划
            logger.warning("[MasterAgent] LLM 规划失败，使用规则兜底: layer=%s error=%s", context.layer, exc)
            return LayerPlan(
                layer=context.layer,
                agents=self._default_agent_tasks(candidates, explicit_set, context),
                reasoning=f"{self._get_layer_name(context.layer)} 使用规则兜底规划",
                fallback_used=True,
            )

    async def _call_llm_for_layer(self, *, context: PlanningContext, candidates: list[str]) -> dict[str, Any]:
        """构造规划提示词并调用 LLM，从返回内容中提取 JSON 格式的层规划。"""

        # 构造当前层的提示词
        prompt = self._build_layer_prompt(context=context, candidates=candidates)

        # 获取规划
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content if hasattr(response, "content") else str(response)
        logger.info(f"[MasterAgent] 规划：resposne=%s", content)
        return parse_first_json_object(content)

    def _sanitize_layer_plan(
        self,
        plan: dict[str, Any],
        candidates: list[str],
        explicit_set: set[str],
        context: PlanningContext,
    ) -> LayerPlan:
        """清洗 LLM 当前层规划，确保只执行合法 Agent。"""

        # 校验 LLM 返回的 layer 编号是否与当前层一致，防止跨层任务泄漏
        if int(plan.get("layer", context.layer)) != context.layer:
            logger.warning("[MasterAgent] LLM 返回跨层规划，使用规则兜底: %s", plan.get("layer"))
            return self._fallback_plan(candidates, explicit_set, context, "LLM 返回了非当前层规划")


        agents = plan.get("agents", [])
        if not isinstance(agents, list) or not agents:
            logger.warning("[MasterAgent] LLM 返回空规划，使用规则兜底")
            return self._fallback_plan(candidates, explicit_set, context, "LLM 返回空规划")

        allowed_dependency_ids = self._allowed_dependency_ids(context)

        sanitized: list[AgentTask] = []
        seen: set[str] = set()
        for index, raw_task in enumerate(agents):
            if not isinstance(raw_task, dict):
                continue
            agent_id = str(raw_task.get("agent_id") or "").strip()
            # 去重检查 + 校验是否在候选列表和用户启用列表中
            if agent_id in seen or agent_id not in candidates or agent_id not in explicit_set:
                continue
            # 合并硬编码依赖 + LLM 动态依赖，去重后仅保留合法的低层依赖
            raw_deps = raw_task.get("depends_on")
            deps = raw_deps if isinstance(raw_deps, list) else []
            deps = [*AGENT_DEPENDENCIES.get(agent_id, []), *deps]
            deduped_deps: list[str] = []
            for dep in deps:
                if isinstance(dep, str) and dep not in deduped_deps:
                    deduped_deps.append(dep)
            allowed_deps = [
                dep
                for dep in deduped_deps
                if isinstance(dep, str) and dep in allowed_dependency_ids
            ]
            # 配置合并优先级：LLM 动态配置 > input_params > 请求级默认配置
            default_config = context.question.agent_configs.model_dump().get(agent_id, {})
            llm_config = raw_task.get("config") if isinstance(raw_task.get("config"), dict) else {}
            input_params = raw_task.get("input_params") if isinstance(raw_task.get("input_params"), dict) else {}
            config = {**llm_config, **input_params, **default_config}
            try:
                priority = int(raw_task.get("priority", index))
            except (TypeError, ValueError):
                priority = index
            priority = max(0, priority)
            task_description = str(raw_task.get("task_description") or self._build_default_task_description(agent_id, context.question.learning_need))
            constraints = raw_task.get("personalized_constraints", [])
            if not isinstance(constraints, list):
                constraints = []
            output_requirements = raw_task.get("output_requirements")
            if not isinstance(output_requirements, dict):
                output_requirements = self._default_output_requirements(agent_id)
            sanitized.append(AgentTask(
                agent_id=agent_id,
                layer=context.layer,
                layer_name=self._get_layer_name(context.layer),
                enabled=bool(raw_task.get("enabled", True)),
                resource_type=str(raw_task.get("resource_type") or agent_id),
                task_description=task_description,
                depends_on=allowed_deps,
                is_explicit=True,
                priority=priority,
                config=config,
                input_params=input_params,
                output_requirements=output_requirements,
                personalized_constraints=[str(item) for item in constraints if item],
                planning_reason=str(raw_task.get("planning_reason") or ""),
                failure_policy=str(raw_task.get("failure_policy") or "skip_on_dependency_failed"),
            ))
            seen.add(agent_id)

        # 过滤掉已禁用的任务，按优先级排序并重新编号
        sanitized = [task for task in sanitized if task.enabled]
        sanitized.sort(key=lambda item: item.priority)
        for index, task in enumerate(sanitized):
            task.priority = index

        if not sanitized:
            logger.warning("[MasterAgent] LLM 规划校验后无合法 Agent，使用规则兜底")
            return self._fallback_plan(candidates, explicit_set, context, "LLM 规划校验后无合法 Agent")

        return LayerPlan(
            layer=context.layer,
            agents=sanitized,
            reasoning=str(plan.get("reasoning") or f"{self._get_layer_name(context.layer)} 规划完成"),
            fallback_used=False,
        )

    def _fallback_plan(
        self,
        candidates: list[str],
        explicit_set: set[str],
        context: PlanningContext,
        reason: str,
    ) -> LayerPlan:
        """LLM 规划失败时的规则兜底：直接按顺序生成默认 AgentTask 列表。"""
        return LayerPlan(
            layer=context.layer,
            agents=self._default_agent_tasks(candidates, explicit_set, context),
            reasoning=f"{reason}，已使用规则兜底",
            fallback_used=True,
        )

    def _default_agent_tasks(
        self,
        candidates: list[str],
        explicit_set: set[str],
        context: PlanningContext,
    ) -> list[AgentTask]:
        """默认 Agent 任务规划：按候选顺序为每个 Agent 生成标准配置的 Task。"""
        learning_need = context.question.learning_need

        tasks = []
        for i, agent_id in enumerate(candidates):
            agent_config = context.question.agent_configs.model_dump().get(agent_id, {})
            task_desc = self._build_default_task_description(agent_id, learning_need)

            tasks.append(AgentTask(
                agent_id=agent_id,
                layer=context.layer,
                layer_name=self._get_layer_name(context.layer),
                task_description=task_desc,
                depends_on=[
                    dep
                    for dep in AGENT_DEPENDENCIES.get(agent_id, [])
                    if dep in self._allowed_dependency_ids(context)
                ],
                is_explicit=agent_id in explicit_set,
                priority=i,
                config=agent_config,
                resource_type=agent_id,
                input_params={"topic": learning_need},
                output_requirements=self._default_output_requirements(agent_id),
                personalized_constraints=self._profile_constraints(context),
                planning_reason=f"{self._get_agent_name(agent_id)}适合支撑{self._get_layer_name(context.layer)}的学习目标。",
                failure_policy="skip_on_dependency_failed",
            ))

        return tasks

    def _build_layer_prompt(self, *, context: PlanningContext, candidates: list[str]) -> str:
        """构造发给 LLM 的层规划提示词，详细约束 Agent 选择的边界条件。"""
        payload = {
            "layer": context.layer,
            "layer_name": self._get_layer_name(context.layer),
            "candidate_agents": candidates,
            "enabled_agents": context.user_explicit_selection,
            "completed_upstream_agents": list(context.upstream_results.keys()),
            "upstream_reports": context.upstream_reports,
            "learning_need": context.question.learning_need,
            "learning_scenario": context.question.learning_scenario.value,
            "agent_configs": context.question.agent_configs.model_dump(),
        }
        return (
            "你是 MasterAgent，只负责规划当前 layer 的多智能体资源生成任务。\n"
            "你不能生成学习资源正文，不能规划其他 layer，不能选择 candidate_agents 之外的 Agent，"
            "也不能选择用户未启用的 Agent。\n"
            "输出必须是严格 JSON，不允许 Markdown、解释文本或代码块。\n"
            "JSON 格式：{\"layer\": 1, \"reasoning\": \"本层规划理由\", \"agents\": ["
            "{\"agent_id\": \"code\", \"enabled\": true, \"task_description\": \"...\", "
            "\"depends_on\": [\"content\"], \"priority\": 0, \"resource_type\": \"code\", "
            "\"input_params\": {}, \"output_requirements\": {}, "
            "\"personalized_constraints\": [], \"planning_reason\": \"...\", "
            "\"failure_policy\": \"skip_on_dependency_failed\"}]}\n\n"
            f"当前规划上下文：{json.dumps(payload, ensure_ascii=False)}"
        )

    def _allowed_dependency_ids(self, context: PlanningContext) -> set[str]:
        """当前层 Agent 只允许依赖已启用的更低层 Agent，禁止跨层或跨用户选择依赖。"""
        lower_layer_agents: set[str] = set()
        for layer, agents in self.LAYER_AGENTS.items():
            if layer < context.layer:
                lower_layer_agents.update(agents)
        return lower_layer_agents & set(context.user_explicit_selection)

    def _default_output_requirements(self, agent_id: str) -> dict[str, Any]:
        """返回每种 Agent 类型的默认输出格式规范和必含字段定义。"""
        requirements = {
            "content": {"format": "markdown", "must_include": ["title", "key_points", "examples"]},
            "mindmap": {"format": "markdown", "must_include": ["central_topic", "branches"]},
            "diagram": {"format": "mermaid", "must_include": ["source", "description"]},
            "code": {"format": "json", "must_include": ["title", "language", "code", "explanation", "run_steps", "exercises"]},
            "reading": {"format": "json", "must_include": ["items", "reason"]},
            "quiz": {"format": "json", "must_include": ["questions", "answers", "analysis"]},
        }
        return requirements.get(agent_id, {"format": "json"})

    def _profile_constraints(self, context: PlanningContext) -> list[str]:
        """根据是否已有上游结果，返回个性化约束提示文本。"""
        if context.upstream_reports:
            return ["结合已生成资源的重点与薄弱点"]
        return ["结合学习者画像生成个性化资源"]

    def _get_layer_name(self, layer: int) -> str:
        """将层编号映射为前端可展示的中文层名称。"""
        names = {0: "认知建构层", 1: "实践拓展层", 2: "检测巩固层"}
        return names.get(layer, f"Layer {layer}")

    def _build_default_task_description(
        self,
        agent_id: str,
        learning_need: str,
    ) -> str:
        """构建默认任务描述：若有学习需求则嵌入需求文本，否则使用泛化描述。"""
        base_desc = f"根据用户学习需求生成{self._get_agent_name(agent_id)}。"

        if learning_need:
            base_desc = f"根据用户需求「{learning_need[:100]}」生成{self._get_agent_name(agent_id)}。"

        return base_desc

    def _get_agent_name(self, agent_id: str) -> str:
        """获取 Agent 中文名称，用于前端展示和规划文案。"""
        names = {
            "content": "课程讲解文档",
            "diagram": "知识图解",
            "mindmap": "思维导图",
            "quiz": "练习题",
            "reading": "拓展阅读推荐",
            "code": "代码实操案例",
        }
        return names.get(agent_id, agent_id)


class ReviewerAgent:
    """资源审查 Agent。检查完整性、质量并生成审查报告。"""

    def review(
        self,
        request: ResourceGenerationRequest,
        resources: list[GeneratedResourceItem],
        failed_agents: list[str],
        errors: list[str],
    ) -> ReviewResult:
        """执行资源审查，返回评分和问题列表。"""
        issues: list[ReviewIssue] = []
        suggestions: list[str] = []
        selected_agents = request.enabled_agent_ids()

        # 空资源检查：没有任何资源产出则直接返回 0 分未通过
        if not resources:
            issues.append(ReviewIssue(
                level="error",
                message="至少应生成一个资源",
                suggestion="请检查 Agent 执行日志",
            ))
            return ReviewResult(passed=False, score=0, issues=issues, suggestions=suggestions)

        # 构建资源类型到资源的映射，便于按类型快速查找和检查
        resource_map = {res.type.value: res for res in resources}

        # 检查启用但未产出的 Agent：用户期望生成但结果缺失的 Agent
        for agent_id in selected_agents:
            if agent_id not in resource_map and agent_id not in failed_agents:
                issues.append(ReviewIssue(
                    resource_type=agent_id,
                    level="warning",
                    message=f"{agent_id} 未产出结果",
                    suggestion="检查 Agent 执行日志",
                ))

        # 检查 quiz
        quiz = resource_map.get("quiz")
        if quiz:
            content = quiz.content
            if isinstance(content, dict):
                questions = content.get("questions", [])
                if not questions:
                    issues.append(ReviewIssue(
                        resource_type="quiz",
                        level="warning",
                        message="quiz 缺少 questions",
                        suggestion="检查习题生成逻辑",
                    ))
                expected = request.agent_configs.quiz.question_count
                if questions and abs(len(questions) - expected) >= max(3, expected // 2):
                    issues.append(ReviewIssue(
                        resource_type="quiz",
                        level="warning",
                        message=f"quiz 题量为 {len(questions)}，与请求数量 {expected} 差距较大",
                        suggestion="按 question_count 重新生成练习题",
                    ))
            elif isinstance(content, str) and not content:
                issues.append(ReviewIssue(
                    resource_type="quiz",
                    level="warning",
                    message="quiz 内容为空",
                    suggestion="检查习题生成逻辑",
                ))

        # 检查 diagram
        diagram = resource_map.get("diagram")
        if diagram:
            content = diagram.content
            if isinstance(content, dict):
                source = content.get("source") or content.get("mermaid")
                if not source:
                    issues.append(ReviewIssue(
                        resource_type="diagram",
                        level="warning",
                        message="diagram 缺少 mermaid source",
                        suggestion="检查图解生成逻辑",
                    ))
            elif isinstance(content, str):
                if not content:
                    issues.append(ReviewIssue(
                        resource_type="diagram",
                        level="warning",
                        message="diagram 内容为空",
                        suggestion="检查图解生成逻辑",
                    ))

        # 检查 code
        code = resource_map.get("code")
        if code:
            content = code.content
            if isinstance(content, dict):
                code_text = content.get("code")
                if not code_text:
                    issues.append(ReviewIssue(
                        resource_type="code",
                        level="warning",
                        message="code 缺少 code 字段",
                        suggestion="检查代码生成逻辑",
                    ))
                language = str(content.get("language", "")).lower()
                expected_language = request.agent_configs.code.programming_language.lower()
                if language and language != expected_language:
                    issues.append(ReviewIssue(
                        resource_type="code",
                        level="warning",
                        message=f"code 语言为 {language}，与请求语言 {expected_language} 不一致",
                        suggestion="检查 CodeAgent 配置传递",
                    ))

        for agent_id in failed_agents:
            issues.append(ReviewIssue(
                resource_type=agent_id,
                level="warning",
                message=f"{agent_id} 生成失败",
                suggestion="可单独重试该资源 Agent",
            ))

        for error in errors:
            suggestions.append(error)

        # 计算综合评分：基于成功数、错误数、警告数的加权计算公式
        success_count = len(resources)
        total_count = len(selected_agents)
        error_count = sum(1 for i in issues if i.level == "error")
        warning_count = sum(1 for i in issues if i.level == "warning")

        # 有错误或全部失败 → 0 分；全部成功无警告 → 95 分高分
        if error_count > 0 or success_count == 0:
            score = 0
        elif warning_count == 0 and success_count == total_count:
            score = 95
        elif failed_agents:
            score = min(69, max(40, int((success_count / total_count) * 70)))
        elif warning_count == 0:
            score = 80 + (success_count / total_count) * 15
        else:
            score = max(40, 70 - warning_count * 5)

        # 根据检查结果生成面向用户的改进建议
        if warning_count > 0:
            suggestions.append("部分资源可能不完整，建议检查后重新生成")
        if success_count < total_count:
            suggestions.append("部分 Agent 执行失败，可以尝试单独重新生成")

        passed = success_count > 0 and error_count == 0
        return ReviewResult(
            passed=passed,
            score=int(score),
            issues=issues,
            suggestions=suggestions,
        )


class AssemblerAgent:
    """资源包组装 Agent。整合资源、生成学习路径、计算最终状态。"""

    def assemble(
        self,
        task_id: str,
        resource_id: str,
        request: ResourceGenerationRequest,
        resources: list[GeneratedResourceItem],
        review_result: ReviewResult,
        failed_agents: list[str],
    ) -> ResourceBundle:
        """组装资源包，生成最终输出结构。"""
        # 生成标题：优先使用请求中指定的标题，否则使用默认名称
        title = request.output_options.final_bundle_title
        if not title:
            title = "个性化学习资源包"

        # 构建学习路径：按 STUDY_PATH_ORDER 固定顺序排列已生成资源
        study_path: list[StudyPathStep] = []
        if request.output_options.include_study_path:
            study_path = self._build_study_path(resources)

        # 计算最终状态：全部成功/部分失败/全部失败三种状态
        if not resources:
            status = "failed"                 # 无任何资源产出
        elif failed_agents:
            status = "partial_completed"      # 部分 Agent 执行失败
        else:
            status = "completed"              # 全部成功

        # 仅保留用户显式启用且已标记 enabled 的 Agent 选择
        selected_agents = [x for x in request.selected_agents if x.enabled]

        return ResourceBundle(
            id=str(resource_id),
            task_id=task_id,
            title=title,
            learning_need=request.learning_need,
            selected_agents=selected_agents,
            resources=resources,
            study_path=study_path,
            review_result=review_result if request.output_options.include_review_result else None,
            status=status,
            metadata={
                "agent_count": len(resources),
                "failed_agents": failed_agents,
            },
        )

    def _build_study_path(self, resources: list[GeneratedResourceItem]) -> list[StudyPathStep]:
        """构建学习路径。"""
        resource_types = {res.type for res in resources}
        path: list[StudyPathStep] = []

        step_titles = {
            "content": "先阅读课程讲解文档",
            "diagram": "查看知识图解",
            "mindmap": "浏览思维导图",
            "code": "学习代码实操案例",
            "quiz": "完成练习题",
            "reading": "阅读拓展材料",
        }

        step_reasons = {
            "content": "建立对主题的整体理解",
            "diagram": "通过可视化加深理解",
            "mindmap": "梳理知识结构",
            "code": "通过实践加深理解",
            "quiz": "检验学习效果",
            "reading": "扩展知识面",
        }

        order = 1
        for resource_type in STUDY_PATH_ORDER:
            if resource_type in resource_types:
                path.append(StudyPathStep(
                    order=order,
                    resource_type=ResourceAgentId(resource_type),
                    title=step_titles.get(resource_type, f"学习 {resource_type}"),
                    reason=step_reasons.get(resource_type, "巩固学习"),
                    estimated_time=STUDY_PATH_ESTIMATED_TIME.get(resource_type),
                ))
                order += 1

        return path


class ResourceWorkflow:
    """资源生成工作流。协调 MasterAgent、WorkerAgents、ReviewerAgent、AssemblerAgent。"""

    def __init__(self, emitter: AgentEventEmitter, resource_store: Any):
        self.emitter = emitter              # SSE 事件发射器，向客户端推送实时进度
        self.resource_store = resource_store  # 资源持久化存储
        self.master_agent = MasterAgent()     # 任务规划器
        self.reviewer_agent = ReviewerAgent() # 质量审查器
        self.assembler_agent = AssemblerAgent() # 结果组装器

    async def run(self, user_id: int, request: ResourceGenerationRequest) -> dict[str, Any]:
        """执行资源生成工作流，每层动态规划。"""
        ensure_initialized()
        user_explicit_selection = request.enabled_agent_ids()
        task_id = str(uuid4())
        self.emitter.bind_task(task_id)

        # 第一阶段：发送任务创建事件，通知前端资源生成已启动
        await self.emitter.emit_workflow(
            stage="created",
            status="pending",
            message="资源生成任务已创建",
            payload={
                "task_id": task_id,
                "selected_agents": user_explicit_selection,
                "learning_need_preview": request.learning_need[:120],
            },
            progress=0,
        )

        try:
            # 在数据库中创建资源记录，获取持久化的 resource_id
            resource_record = await self.resource_store.create_resource(
                user_id=user_id,
                request=request,
            )
            resource_id = resource_record.id

            # 第二阶段：加载用户画像信息，用于后续个性化资源生成
            await self.emitter.emit_workflow(
                stage="profile",
                status="running",
                message="正在加载学习者画像",
                progress=5,
            )
            snapshot = await load_profile_snapshot(user_id)
            learner_profile = snapshot.as_agent_profile()
            await self.emitter.emit_workflow(
                stage="profile",
                status="success",
                message="学习者画像加载完成",
                progress=8,
                payload={
                    "profile_summary": self._summarize_profile(learner_profile),
                    "has_profile": bool(learner_profile),
                },
            )

            agent_context = {
                "learning_need": request.learning_need,
                "agent_configs": request.agent_configs.model_dump(),
                "selected_agents": user_explicit_selection,
                "learner_profile": learner_profile,
            }

            raw_results: dict[str, dict[str, Any]] = {}
            all_resources: list[GeneratedResourceItem] = []
            failed_agents: list[str] = []
            skipped_agents: list[str] = []
            errors: list[str] = []
            total_layers = 3
            planned_tasks: list[AgentTask] = []
            planned_agent_ids: set[str] = set()

            # 第三阶段：逐层规划，收集所有 AgentTask；执行阶段交给 DAG 调度器
            for layer in range(total_layers):
                layer_name = self._get_layer_name(layer)
                # 筛选当前层中用户启用且已注册实现的候选 Agent
                candidate_agents = [
                    agent for agent in MasterAgent.LAYER_AGENTS.get(layer, [])
                    if agent in user_explicit_selection and agent in AGENT_CLASS_MAP
                ]
                upstream_reports = self._build_upstream_reports(raw_results)
                # 发送规划中事件，通知前端 MasterAgent 正在分析当前层
                await self.emitter.emit_event(
                    event_type="planning",
                    stage="planning",
                    agent="master",
                    status="running",
                    message=f"MasterAgent 正在规划 {layer_name}",
                    progress=8 + layer * 3,
                    payload={
                        "layer": layer,
                        "layer_name": layer_name,
                        "candidate_agents": candidate_agents,
                        "upstream_agents": list(planned_agent_ids),
                        "has_upstream_results": bool(raw_results),
                        "planning_mode": "layer_dynamic",
                    },
                )
                # 构建当前层规划上下文：包含层号、请求、上游结果和交接报告
                planning_context = PlanningContext(
                    layer=layer,
                    question=request,
                    user_explicit_selection=user_explicit_selection,
                    implicit_dependencies=[],
                    upstream_results=raw_results,
                    upstream_reports=upstream_reports,
                )

                layer_plan = await self.master_agent.plan_layer(planning_context)

                # 发送规划完成事件，展示 MasterAgent 的推理和 Agent 选择结果
                await self.emitter.emit_event(
                    event_type="planning",
                    stage="planning",
                    agent="master",
                    status="success",
                    message=f"{layer_name} 规划完成",
                    payload={
                        "layer": layer,
                        "layer_name": layer_name,
                        "reasoning": layer_plan.reasoning,
                        "agents": [self._serialize_agent_task(task) for task in layer_plan.agents],
                        "fallback_used": layer_plan.fallback_used,
                    },
                    progress=10 + int((layer + 1) / total_layers * 5),
                )

                # 当前层无待执行 Agent 时跳过，不阻塞后续层
                if not layer_plan.agents:
                    await self.emitter.emit_workflow(
                        stage=self._get_layer_stage(layer),
                        status="skipped",
                        message=f"{layer_name}无可执行 Agent",
                        payload={"layer": layer, "layer_name": layer_name, "agents": []},
                    )
                    continue

                # 收集所有层的规划任务，统一提交给 DAG 执行引擎
                for agent_task in layer_plan.agents:
                    planned_tasks.append(agent_task)
                    planned_agent_ids.add(agent_task.agent_id)

            await self._execute_planned_tasks_dag(
                planned_tasks=planned_tasks,
                user_id=user_id,
                resource_id=resource_id,
                request=request,
                agent_context=agent_context,
                raw_results=raw_results,
                all_resources=all_resources,
                failed_agents=failed_agents,
                skipped_agents=skipped_agents,
                errors=errors,
                user_explicit_selection=user_explicit_selection,
                base_progress=15,
                max_progress=90,
            )

            # 全部 Agent 失败但无资源时的兜底错误提示
            if not all_resources and failed_agents:
                errors.append("所有启用 Agent 均未成功生成资源")

            # 仅保留用户显式选择类型的资源，排除隐式依赖产出的中间资源
            explicit_resources = [
                r for r in all_resources
                if r.type.value in user_explicit_selection
            ]

            # 全部显式资源失败/跳过时发送失败事件通知前端
            if not explicit_resources and skipped_agents:
                await self.emitter.emit_event(
                    event_type="workflow",
                    stage="failed",
                    status="failed",
                    message="所有资源生成任务均失败或被跳过",
                    payload={
                        "failed_agents": failed_agents,
                        "skipped_agents": skipped_agents,
                    },
                )

            # 第四阶段：ReviewerAgent 审查所有已生成资源的质量
            await self.emitter.emit_event(
                event_type="review",
                stage="reviewing",
                status="running",
                message="ReviewerAgent 正在审查资源质量",
                agent="reviewer",
                progress=92,
            )

            # 合并失败和跳过的 Agent 列表（去重保持顺序）
            failed_or_skipped_agents = list(dict.fromkeys([*failed_agents, *skipped_agents]))
            review_result = self.reviewer_agent.review(
                request=request,
                resources=explicit_resources,
                failed_agents=failed_or_skipped_agents,
                errors=errors,
            )

            # 发送审查结果事件，前端展示评分和质量问题
            await self.emitter.emit_review(review_result=review_result, progress=95)

            # 第五阶段：AssemblerAgent 组装最终资源包
            await self.emitter.emit_event(
                event_type="bundle",
                stage="assembling",
                status="running",
                message="AssemblerAgent 正在组装资源包",
                agent="assembler",
                progress=97,
            )

            bundle = self.assembler_agent.assemble(
                task_id=task_id,
                resource_id=str(resource_id),
                request=request,
                resources=explicit_resources,
                review_result=review_result,
                failed_agents=failed_or_skipped_agents,
            )

            # 持久化更新资源状态（completed / partial_completed / failed）
            await self.resource_store.update_resource_status(
                resource_id=resource_id,
                status=bundle.status,
            )

            # 发送资源包和完成事件，通知前端展示最终结果
            await self.emitter.emit_bundle(bundle=bundle, progress=99)
            await self.emitter.emit_done(bundle=bundle)

            return {"success": bundle.status != "failed", "results": raw_results, "bundle": bundle.model_dump(mode="json")}

        except Exception as exc:
            # 全局异常捕获：记录日志、发送错误事件、安全关闭 emitter
            logger.exception("[ResourceWorkflow] 执行失败")
            await self.emitter.emit_error(message=str(exc))
            await self.emitter.close()
            return {"success": False, "results": {}, "error": str(exc)}

    async def _execute_agent_task(
        self,
        *,
        agent_task: AgentTask,
        user_id: int,
        resource_id: int,
        request: ResourceGenerationRequest,
        agent_context: dict[str, Any],
        upstream_results: dict[str, dict[str, Any]],
        layer_index: int = 0,
        layer_name: str = "认知建构层",
        layer_stage: str = "layer_0",
        degraded: bool = False,
        missing_dependencies: list[str] | None = None,
        failed_dependencies: list[str] | None = None,
    ) -> tuple[str, dict[str, Any], bool, AgentTask]:
        """执行单个 AgentTask 并返回结果。"""
        agent_id = agent_task.agent_id
        agent_cls = AGENT_CLASS_MAP.get(agent_id)
        # 未知 Agent 类型直接返回失败，不执行
        if agent_cls is None:
            return agent_id, {"success": False, "error": f"Unknown agent: {agent_id}"}, agent_task.is_explicit, agent_task

        # 绑定 Agent 和层阶段，确保事件正确路由到前端 SSE 流
        self.emitter.bind_agent_stage(agent_id, layer_stage)
        await self.emitter.emit_agent(
            agent=agent_id,
            status="running",
            message=f"{self._get_agent_role_name(agent_id)}正在生成资源",
            stage=layer_stage,
            payload={
                "layer": layer_index,
                "layer_name": layer_name,
                "agent_id": agent_id,
                "agent_role": self._get_agent_role_name(agent_id),
                "task_description": agent_task.task_description,
                "depends_on": agent_task.depends_on,
                "resource_type": agent_task.resource_type or agent_id,
                "upstream_agents": list(upstream_results.keys()),
                "has_profile": bool(agent_context.get("learner_profile", {})),
                "learning_need_preview": request.learning_need[:120],
                "input_params": agent_task.input_params,
                "output_requirements": agent_task.output_requirements,
                "personalized_constraints": agent_task.personalized_constraints,
                "planning_reason": agent_task.planning_reason,
                "current_action": "接收任务并准备生成",
                "current_step": 1,
                "total_steps": 5,
                "step_label": "接收任务",
                "output_preview": "已接收 MasterAgent 规划任务，准备结合画像和上游资源生成内容",
            },
        )

        # 实例化具体的 Worker Agent（如 ContentAgent、CodeAgent 等）
        worker = agent_cls(user_id, resource_id, emitter=self.emitter)

        # 构造任务载荷：学习需求 + MasterAgent 的任务描述和规划理由
        task_payload = {
            "learning_need": request.learning_need,
            "task_description": agent_task.task_description,
            "planning_reason": agent_task.planning_reason,
        }
        # 收集依赖 Agent 的执行报告，供当前 Agent 了解上下游进展
        dependency_reports = {
            dep: upstream_results[dep].get("execution_report") or upstream_results[dep].get("summary", "")
            for dep in AGENT_DEPENDENCIES.get(agent_id, [])
            if dep in upstream_results
        }

        # 构建 WorkerState：包含所有执行上下文，传递给 Worker Agent 的 run 方法
        state = WorkerState(
            user_id=user_id,
            resource_id=resource_id,
            agent_name=agent_id,
            task=task_payload,
            learner_profile=agent_context.get("learner_profile", {}),
            agent_config=agent_task.config,
            workflow_plan=[],
            layer_index=layer_index,
            upstream_results=upstream_results,
            dependency_reports=dependency_reports,
            learning_scenario=request.learning_scenario.value,
            planner_input_params=agent_task.input_params,
            output_requirements=agent_task.output_requirements,
            personalized_constraints=agent_task.personalized_constraints,
            degraded=degraded,                    # 降级模式：依赖失败时仍尝试运行
            missing_dependencies=missing_dependencies or [],
            failed_dependencies=failed_dependencies or [],
        )

        result = await worker.run(state)
        return agent_id, result.model_dump() if hasattr(result, "model_dump") else dict(result), agent_task.is_explicit, agent_task

    async def _execute_planned_tasks_dag(
        self,
        *,
        planned_tasks: list[AgentTask],
        user_id: int,
        resource_id: int,
        request: ResourceGenerationRequest,
        agent_context: dict[str, Any],
        raw_results: dict[str, dict[str, Any]],
        all_resources: list[GeneratedResourceItem],
        failed_agents: list[str],
        skipped_agents: list[str],
        errors: list[str],
        user_explicit_selection: list[str],
        base_progress: int = 15,
        max_progress: int = 90,
    ) -> None:
        """按 DAG 依赖 ready 即触发执行，不再等待整层完成。"""
        # 初始化任务跟踪状态：待执行、执行中、已完成、已失败、已跳过
        pending_agents: dict[str, AgentTask] = {task.agent_id: task for task in planned_tasks if task.enabled}
        running_agents: dict[asyncio.Task[tuple[str, dict[str, Any], bool, AgentTask]], AgentTask] = {}
        completed_agents: set[str] = set()
        failed_agent_set: set[str] = set()
        skipped_agent_set: set[str] = set()
        all_agent_ids = set(pending_agents)
        # 层状态追踪：记录每层的开始、终端（成功/失败/跳过）计数
        layer_started: set[int] = set()
        layer_terminal: dict[int, set[str]] = {}
        layer_completed: dict[int, set[str]] = {}
        layer_failed: dict[int, set[str]] = {}
        layer_skipped: dict[int, set[str]] = {}
        total_agents = len(pending_agents)

        # 无任何待执行 Agent，直接发送跳过事件
        if total_agents == 0:
            await self.emitter.emit_workflow(
                stage="layer_0",
                status="skipped",
                message="没有可执行的资源生成 Agent",
                payload={"completed_agents": [], "failed_agents": [], "skipped_agents": []},
                progress=base_progress,
            )
            return

        def terminal_count() -> int:
            return len(completed_agents) + len(failed_agent_set) + len(skipped_agent_set)

        def progress() -> int:
            ratio = terminal_count() / total_agents if total_agents else 1
            return min(max_progress, base_progress + int(ratio * (max_progress - base_progress)))

        async def mark_layer_started(task: AgentTask) -> None:
            layer = task.layer
            if layer in layer_started:
                return
            layer_started.add(layer)
            layer_name = task.layer_name or self._get_layer_name(layer)
            layer_tasks = [item for item in planned_tasks if item.layer == layer and item.enabled]
            await self.emitter.emit_workflow(
                stage=self._get_layer_stage(layer),
                status="running",
                message=f"开始执行{layer_name}",
                payload={
                    "layer": layer,
                    "layer_name": layer_name,
                    "agents": [self._serialize_agent_task(item) for item in layer_tasks],
                    "schedule_mode": "dag_dependency_ready",
                },
                progress=progress(),
            )

        async def mark_agent_skipped(
            task: AgentTask,
            *,
            skipped_reason: str,
            missing_dependencies: list[str],
            failed_dependencies: list[str],
        ) -> None:
            pending_agents.pop(task.agent_id, None)
            skipped_agent_set.add(task.agent_id)
            if task.agent_id not in skipped_agents:
                skipped_agents.append(task.agent_id)
            layer = task.layer
            layer_name = task.layer_name or self._get_layer_name(layer)
            layer_stage = self._get_layer_stage(layer)
            self.emitter.bind_agent_stage(task.agent_id, layer_stage)
            await self.emitter.emit_agent(
                agent=task.agent_id,
                status="skipped",
                stage=layer_stage,
                message=f"{self._get_agent_role_name(task.agent_id)}因依赖未满足已跳过",
                payload={
                    "skipped_reason": skipped_reason,
                    "missing_dependencies": missing_dependencies,
                    "failed_dependencies": failed_dependencies,
                    "layer": layer,
                    "layer_name": layer_name,
                    "agent_id": task.agent_id,
                    "agent_role": self._get_agent_role_name(task.agent_id),
                    "depends_on": task.depends_on,
                    "task_description": task.task_description,
                    "schedule_mode": "dependency_failed",
                },
            )
            await mark_layer_terminal(task, status="skipped")

        async def mark_layer_terminal(task: AgentTask, *, status: str) -> None:
            layer = task.layer
            layer_terminal.setdefault(layer, set()).add(task.agent_id)
            if status == "success":
                layer_completed.setdefault(layer, set()).add(task.agent_id)
            elif status == "failed":
                layer_failed.setdefault(layer, set()).add(task.agent_id)
            elif status == "skipped":
                layer_skipped.setdefault(layer, set()).add(task.agent_id)

            layer_tasks = [item for item in planned_tasks if item.layer == layer and item.enabled]
            if len(layer_terminal[layer]) < len(layer_tasks):
                return

            completed = sorted(layer_completed.get(layer, set()))
            failed = sorted(layer_failed.get(layer, set()))
            skipped = sorted(layer_skipped.get(layer, set()))
            if completed:
                workflow_status = "success"
            elif failed:
                workflow_status = "failed"
            else:
                workflow_status = "skipped"
            layer_name = task.layer_name or self._get_layer_name(layer)
            await self.emitter.emit_workflow(
                stage=self._get_layer_stage(layer),
                status=workflow_status,
                message=f"{layer_name}执行完成",
                payload={
                    "layer": layer,
                    "layer_name": layer_name,
                    "completed_agents": completed,
                    "failed_agents": failed,
                    "skipped_agents": skipped,
                    "schedule_mode": "dag_dependency_ready",
                },
                progress=progress(),
            )

        def dependency_state(task: AgentTask) -> tuple[bool, bool, list[str], list[str]]:
            """检查 Agent 依赖是否满足，返回 (ready, degraded, missing_deps, failed_deps)。

            根据 failure_policy 决定依赖不满足时的行为：
            - skip_on_dependency_failed → 跳过该 Agent
            - degraded_run → 以降级模式运行
            - ignore_dependency → 忽略失败依赖继续运行
            """
            deps = task.depends_on or []
            missing = [dep for dep in deps if dep not in all_agent_ids]
            failed_deps = [dep for dep in deps if dep in failed_agent_set or dep in skipped_agent_set]
            unfinished = [
                dep
                for dep in deps
                if dep in all_agent_ids
                and dep not in completed_agents
                and dep not in failed_agent_set
                and dep not in skipped_agent_set
            ]
            if missing or failed_deps:
                if task.failure_policy == "skip_on_dependency_failed":
                    return False, False, missing, failed_deps
                if task.failure_policy == "degraded_run" and not unfinished:
                    return True, bool(missing or failed_deps), missing, failed_deps
                if task.failure_policy == "ignore_dependency" and not unfinished:
                    return True, False, missing, failed_deps
                return False, False, missing, failed_deps
            return not unfinished, False, [], []

        async def schedule_ready_agents() -> None:
            """扫描所有 pending Agent，将依赖已满足的 Agent 提交执行。

            在同一轮中尽可能多地调度 Agent，最大化并行度。
            """
            while True:
                scheduled_any = False
                for task in list(pending_agents.values()):
                    ready, degraded, missing_deps, failed_deps = dependency_state(task)
                    if not ready:
                        # 依赖不满足且策略为跳过时，标记为已跳过
                        if (missing_deps or failed_deps) and task.failure_policy == "skip_on_dependency_failed":
                            await mark_agent_skipped(
                                task,
                                skipped_reason="依赖 Agent 失败或缺失，当前策略为 skip_on_dependency_failed",
                                missing_dependencies=missing_deps,
                                failed_dependencies=failed_deps,
                            )
                            scheduled_any = True
                        continue

                    pending_agents.pop(task.agent_id, None)
                    await mark_layer_started(task)
                    layer = task.layer
                    layer_name = task.layer_name or self._get_layer_name(layer)
                    layer_stage = self._get_layer_stage(layer)
                    triggered_by = [dep for dep in task.depends_on if dep in completed_agents]
                    await self.emitter.emit_agent(
                        agent=task.agent_id,
                        status="running",
                        stage=layer_stage,
                        message=f"{self._get_agent_role_name(task.agent_id)} 依赖 {', '.join(task.depends_on) or '无'} 已满足，开始生成资源",
                        payload={
                            "schedule_mode": "dependency_ready",
                            "depends_on": task.depends_on,
                            "triggered_by": triggered_by,
                            "layer": layer,
                            "layer_name": layer_name,
                            "agent_id": task.agent_id,
                            "agent_role": self._get_agent_role_name(task.agent_id),
                            "task_description": task.task_description,
                            "planning_reason": task.planning_reason,
                            "degraded": degraded,
                            "missing_dependencies": missing_deps,
                            "failed_dependencies": failed_deps,
                        },
                    )
                    running = asyncio.create_task(
                        self._execute_agent_task(
                            agent_task=task,
                            user_id=user_id,
                            resource_id=resource_id,
                            request=request,
                            agent_context=agent_context,
                            upstream_results=dict(raw_results),
                            layer_index=layer,
                            layer_name=layer_name,
                            layer_stage=layer_stage,
                            degraded=degraded,
                            missing_dependencies=missing_deps,
                            failed_dependencies=failed_deps,
                        )
                    )
                    running_agents[running] = task
                    scheduled_any = True
                if not scheduled_any:
                    break

        # 主调度循环：持续调度就绪 Agent，等待执行完成，直到所有任务终结
        while pending_agents or running_agents:
            await schedule_ready_agents()
            # 无执行中的 Agent 时，剩余 pending 全部标记为跳过（死锁保护）
            if not running_agents:
                for task in list(pending_agents.values()):
                    await mark_agent_skipped(
                        task,
                        skipped_reason="依赖关系无法满足或存在循环依赖",
                        missing_dependencies=[dep for dep in task.depends_on if dep not in all_agent_ids],
                        failed_dependencies=[dep for dep in task.depends_on if dep in failed_agent_set or dep in skipped_agent_set],
                    )
                continue

            # 等待任意一个 Agent 完成，立刻处理其产物，触发下游依赖检查
            done, _ = await asyncio.wait(running_agents.keys(), return_when=asyncio.FIRST_COMPLETED)
            for finished in done:
                task = running_agents.pop(finished)
                layer_stage = self._get_layer_stage(task.layer)
                layer_name = task.layer_name or self._get_layer_name(task.layer)
                try:
                    agent_id, result, is_explicit, agent_task = finished.result()
                except Exception as exc:
                    agent_id = task.agent_id
                    result = {"success": False, "error": str(exc)}
                    is_explicit = task.is_explicit
                    agent_task = task

                raw_results[agent_id] = result
                if result.get("success"):
                    # 成功时：保存产物到数据库并记录到 all_resources
                    try:
                        saved_item = await self._save_successful_agent_result(
                            agent_id=agent_id,
                            result=result,
                            is_explicit=is_explicit,
                            agent_task=agent_task,
                            resource_id=resource_id,
                            user_id=user_id,
                            request=request,
                            layer_stage=layer_stage,
                        )
                    except Exception as exc:
                        # 保存失败时回退标记为失败
                        saved_item = None
                        result = {"success": False, "error": str(exc)}
                        raw_results[agent_id] = result

                    if saved_item is not None:
                        completed_agents.add(agent_id)
                        all_resources.append(saved_item)
                        await mark_layer_terminal(agent_task, status="success")
                        continue

                # 失败处理：记录到失败集合和错误列表，发送失败事件
                failed_agent_set.add(agent_id)
                if agent_id not in failed_agents:
                    failed_agents.append(agent_id)
                error = f"{agent_id} 生成失败: {result.get('error', 'unknown')}"
                errors.append(error)
                await self.emitter.emit_agent(
                    agent=agent_id,
                    status="failed",
                    stage=layer_stage,
                    message=f"{self._get_agent_role_name(agent_id)}生成失败",
                    payload={
                        "error": result.get("error", "unknown"),
                        "layer": agent_task.layer,
                        "layer_name": layer_name,
                        "task_description": agent_task.task_description,
                    },
                )
                await mark_layer_terminal(agent_task, status="failed")

    async def _finalize_layer_results(
        self,
        *,
        layer_results: list[Any],
        resource_id: int,
        user_id: int,
        request: ResourceGenerationRequest,
        all_resources: list[GeneratedResourceItem],
        content_markdown: str | None,
        code_content: Any,
        failed_agents: list[str],
        errors: list[str],
        layer_index: int = 0,
        layer_name: str = "认知建构层",
        layer_stage: str = "layer_0",
        raw_results: dict[str, dict[str, Any]] | None = None,
    ) -> tuple[str | None, Any]:
        """并发保存同一层成功产物，并收集失败信息。"""
        save_inputs = []

        for item_result in layer_results:
            if isinstance(item_result, Exception):
                errors.append(str(item_result))
                await self.emitter.emit_error(stage=layer_stage, message=str(item_result))
                continue

            if len(item_result) == 3:
                agent_id, result, is_explicit = item_result
                agent_task = AgentTask(
                    agent_id=agent_id,
                    task_description=f"执行 {agent_id} 资源生成",
                    depends_on=AGENT_DEPENDENCIES.get(agent_id, []),
                    is_explicit=is_explicit,
                    resource_type=agent_id,
                    config=request.agent_configs.model_dump().get(agent_id, {}),
                )
            else:
                agent_id, result, is_explicit, agent_task = item_result
            if raw_results is not None:
                raw_results[agent_id] = result

            if result.get("success"):
                save_inputs.append(
                    (
                        agent_id,
                        result,
                        is_explicit,
                        agent_task,
                    )
                )
                continue

            failed_agents.append(agent_id)
            errors.append(f"{agent_id} 生成失败: {result.get('error', 'unknown')}")
            await self.emitter.emit_agent(
                agent=agent_id,
                status="failed",
                stage=layer_stage,
                message=f"{self._get_agent_role_name(agent_id)}生成失败",
                payload={
                    "error": result.get("error", "unknown"),
                    "layer": layer_index,
                    "layer_name": layer_name,
                    "task_description": agent_task.task_description,
                },
            )

        saved_results = []
        for agent_id, result, is_explicit, agent_task in save_inputs:
            try:
                saved_item = await self._save_successful_agent_result(
                    agent_id=agent_id,
                    result=result,
                    is_explicit=is_explicit,
                    agent_task=agent_task,
                    resource_id=resource_id,
                    user_id=user_id,
                    request=request,
                    layer_stage=layer_stage,
                )
                saved_results.append((agent_id, saved_item, None))
            except Exception as exc:
                saved_results.append((agent_id, None, str(exc)))

        for agent_id, resource_item, error in saved_results:
            if error:
                errors.append(error)
                await self.emitter.emit_error(stage=layer_stage, message=error)
                continue
            if resource_item is None:
                failed_agents.append(agent_id)
                continue
            all_resources.append(resource_item)
            # 提取 content（markdown 文本）和 code（结构化数据）供 quiz Agent 使用
            if agent_id == "content":
                content_markdown = resource_item.content if isinstance(resource_item.content, str) else None
            elif agent_id == "code":
                code_content = resource_item.content

        return content_markdown, code_content

    async def _save_successful_agent_result(
        self,
        *,
        agent_id: str,
        result: dict[str, Any],
        is_explicit: bool,
        agent_task: AgentTask,
        resource_id: int,
        user_id: int,
        request: ResourceGenerationRequest,
        layer_stage: str,
    ) -> GeneratedResourceItem | None:
        """保存单个成功 Agent 的产物并发出完成事件。"""
        resource_item = self._build_resource_item(
            agent_id=agent_id,
            result=result,
            depends_on=agent_task.depends_on,
            request=request,
            agent_task=agent_task,
        )
        try:
            saved_item = await self.resource_store.save_resource_item(
                resource_id=resource_id,
                user_id=user_id,
                item=resource_item,
            )
            if saved_item.id is not None:
                resource_item.id = str(saved_item.id)
            await self.emitter.emit_agent(
                agent=agent_id,
                status="success",
                stage=layer_stage,
                message=f"{self._get_agent_role_name(agent_id)}生成完成",
                payload={
                    "resource_id": resource_item.id,
                    "resource_type": resource_item.type.value,
                    "title": resource_item.title,
                    "summary": resource_item.summary,
                    "output_preview": self._preview_output(resource_item.content),
                    "is_explicit": is_explicit,
                },
            )
            await self.emitter.emit_resource(
                agent=agent_id,
                resource=resource_item,
                stage=layer_stage,
                message=f"{self._get_agent_role_name(agent_id)}生成完成",
            )
            return resource_item
        except Exception as save_exc:
            await self.emitter.emit_agent(
                agent=agent_id,
                status="failed",
                stage=layer_stage,
                message=f"{self._get_agent_role_name(agent_id)}数据库保存失败",
            )
            raise RuntimeError(f"{agent_id} 保存失败: {save_exc}") from save_exc

    def _build_resource_item(
        self,
        *,
        agent_id: str,
        result: dict[str, Any],
        depends_on: list[str],
        request: ResourceGenerationRequest,
        agent_task: AgentTask | None = None,
    ) -> GeneratedResourceItem:
        """构建资源项，标准化不同类型的内容格式。"""
        raw_content = result.get("content", "")
        parsed_content: Any = raw_content
        fmt = self._infer_format(agent_id, result)

        # 根据 Agent 类型对原始内容做标准化处理：图解、代码、阅读为结构化 JSON
        if agent_id == "diagram":
            parsed_content = self._normalize_diagram_content(raw_content, request)
            fmt = "mermaid" if parsed_content.get("render_format") == "mermaid" else "json"
        elif agent_id == "code":
            parsed_content = self._normalize_code_content(raw_content, request)
            fmt = "json"
        elif agent_id == "reading":
            parsed_content = self._normalize_reading_content(raw_content)
            fmt = "json"
        elif fmt == "json":
            # 通用 JSON 解析：字符串尝试反序列化，失败则包裹为原始文本对象
            try:
                parsed_content = json.loads(raw_content) if isinstance(raw_content, str) else raw_content
            except Exception:
                parsed_content = {"raw": raw_content}

        # 构建元数据：合并 Agent 结果中的 metadata 和默认元数据字段
        summary = f"{agent_id} 资源已生成"
        metadata = dict(result.get("metadata") or {})
        metadata.update({
            "agent": f"{agent_id.capitalize()}Agent",
            "agent_role": self._get_agent_role_name(agent_id),
            "depends_on": depends_on,
            "knowledge_points": self._extract_knowledge_points(agent_id, result, agent_task),
            "difficulty": metadata.get("difficulty") or self._default_difficulty(agent_id),
            "suitable_stage": metadata.get("suitable_stage") or self._default_stage(agent_id),
            "estimated_time": metadata.get("estimated_time") or STUDY_PATH_ESTIMATED_TIME.get(agent_id),
            "personalized_reason": (agent_task.planning_reason if agent_task else None) or metadata.get("personalized_reason") or "",
            "learning_objectives": metadata.get("learning_objectives") or self._default_learning_objectives(agent_id),
            "prerequisites": metadata.get("prerequisites") or depends_on,
            "resource_priority": metadata.get("resource_priority") or self._default_resource_priority(agent_id),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "config": (agent_task.config if agent_task else request.agent_configs.model_dump().get(agent_id, {})),
        })
        return GeneratedResourceItem(
            type=ResourceAgentId(agent_id),
            title=result.get("title") or f"学习资源 - {agent_id}",
            format=fmt,
            content=parsed_content,
            summary=result.get("summary") or summary,
            execution_report=result.get("execution_report"),
            metadata=metadata,
        )

    def _get_agent_role_name(self, agent_id: str) -> str:
        """获取前端可展示的 Agent 角色名，用于 SSE 事件中的 agent 字段。"""
        names = {
            "content": "ContentAgent",
            "mindmap": "MindmapAgent",
            "diagram": "DiagramAgent",
            "code": "CodeAgent",
            "reading": "ReadingAgent",
            "video": "VideoAgent",
            "quiz": "QuizAgent",
        }
        return names.get(agent_id, f"{agent_id.capitalize()}Agent")

    def _get_layer_name(self, layer: int) -> str:
        """将层编号（0/1/2）映射为前端可展示的中文层名称。"""
        names = {0: "认知建构层", 1: "实践拓展层", 2: "检测巩固层"}
        return names.get(layer, f"Layer {layer}")

    def _get_layer_stage(self, layer: int) -> str:
        """将层编号映射为 SSE 事件的 stage 标识字符串。"""
        stages = {0: "layer_0", 1: "layer_1", 2: "layer_2"}
        return stages.get(layer, "planning")

    def _build_upstream_reports(self, raw_results: dict[str, dict[str, Any]]) -> dict[str, str]:
        """把上游原始结果压缩为给 MasterAgent/WorkerAgent 使用的交接报告。"""
        reports: dict[str, str] = {}
        for agent_id, result in raw_results.items():
            # 优先使用 execution_report，其次 summary，最后 content 的前 300 字符预览
            report = result.get("execution_report") or result.get("summary")
            if not report:
                report = self._preview_output(result.get("content"))
            reports[agent_id] = str(report or "")[:1000]
        return reports

    def _default_stage(self, agent_id: str) -> str:
        """返回每种资源类型的默认学习阶段分类。"""
        stages = {
            "content": "concept_understanding",
            "mindmap": "knowledge_structure",
            "diagram": "visual_understanding",
            "code": "practice",
            "quiz": "assessment",
            "reading": "extension",
            "video": "multimodal_understanding",
        }
        return stages.get(agent_id, "resource_generation")

    def _default_difficulty(self, agent_id: str) -> str:
        """返回每种资源类型的默认难度等级。"""
        if agent_id in {"code", "quiz"}:
            return "medium"
        if agent_id == "reading":
            return "extended"
        return "basic"

    def _default_resource_priority(self, agent_id: str) -> int:
        """根据学习路径顺序返回默认资源优先级序号。"""
        order = {agent: index for index, agent in enumerate(STUDY_PATH_ORDER)}
        return order.get(agent_id, 99)

    def _default_learning_objectives(self, agent_id: str) -> list[str]:
        """返回每种资源类型的默认学习目标描述列表。"""
        objectives = {
            "content": ["理解核心概念", "掌握关键知识点"],
            "mindmap": ["建立知识结构", "识别知识点关系"],
            "diagram": ["通过图示理解过程和关系"],
            "code": ["通过实践验证概念", "掌握可运行案例"],
            "quiz": ["检测理解程度", "巩固易错点"],
            "reading": ["拓展相关背景", "连接更多应用场景"],
            "video": ["通过多模态材料辅助理解"],
        }
        return objectives.get(agent_id, ["完成当前资源学习目标"])

    def _extract_knowledge_points(
        self,
        agent_id: str,
        result: dict[str, Any],
        agent_task: AgentTask | None,
    ) -> list[str]:
        """从 Agent 结果或任务参数中提取知识点列表，用于元数据标注。"""
        metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        points = metadata.get("knowledge_points")
        if not points and agent_task:
            points = agent_task.input_params.get("knowledge_points")
        if isinstance(points, list):
            return [str(item) for item in points if item]
        return [agent_id]

    def _summarize_profile(self, learner_profile: dict[str, Any]) -> dict[str, Any]:
        """将详细的学习者画像压缩为前端可展示的摘要字典。"""
        if not learner_profile:
            return {}
        # 优先提取 profile_json 中各维度的 summary 字段
        profile_json = learner_profile.get("profile_json")
        if isinstance(profile_json, dict):
            dimensions = profile_json.get("dimensions")
            if isinstance(dimensions, dict):
                return {
                    key: value.get("summary")
                    for key, value in dimensions.items()
                    if isinstance(value, dict) and value.get("summary")
                }
        # 无 profile_json 时回退到基础用户信息字段
        return {key: learner_profile.get(key) for key in ("username", "major", "grade", "confidence") if learner_profile.get(key)}

    def _serialize_agent_task(self, task: AgentTask) -> dict[str, Any]:
        """将 AgentTask 序列化为字典，附加 agent_role 字段供前端展示。"""
        payload = task.model_dump(mode="json")
        payload["agent_role"] = self._get_agent_role_name(task.agent_id)
        return payload

    def _preview_output(self, value: Any, max_len: int = 300) -> str:
        """将任意输出值截取为前端可预览的短字符串（换行转空格）。"""
        try:
            if isinstance(value, str):
                text = value
            else:
                text = json.dumps(value, ensure_ascii=False)
        except Exception:
            text = str(value)
        text = text.replace("\n", " ").strip()
        return text[:max_len] + ("..." if len(text) > max_len else "")

    def _infer_format(self, agent_id: str, result: dict[str, Any]) -> str:
        """根据 Agent 类型和结果推断资源格式（markdown/mermaid/json）。"""
        # 预定义类型的直接映射
        if agent_id in {"content", "mindmap"}:
            return "markdown"
        if agent_id == "diagram":
            return "mermaid"
        if agent_id in {"quiz", "reading", "code"}:
            return "json"
        # 兜底：根据结果中的 file_type 字段推断
        file_type = str(result.get("file_type", "")).lower()
        if file_type in {"md", "markdown"}:
            return "markdown"
        if file_type == "mermaid":
            return "mermaid"
        if file_type == "json":
            return "json"
        return "json"

    def _normalize_diagram_content(self, raw_content: Any, request: ResourceGenerationRequest) -> dict[str, Any]:
        """标准化 diagram 内容为统一格式 {diagram_type, render_format, source, description}。"""
        if isinstance(raw_content, dict):
            # 已经是标准格式，直接返回
            if "source" in raw_content:
                return raw_content
            # 从 render 嵌套结构中提取
            render = raw_content.get("render")
            if isinstance(render, dict) and render.get("source"):
                return {
                    "diagram_type": raw_content.get("diagram_type") or raw_content.get("type") or request.agent_configs.diagram.diagram_type,
                    "render_format": render.get("engine", "mermaid"),
                    "source": render.get("source", ""),
                    "description": raw_content.get("description") or raw_content.get("summary", "知识图解"),
                }
        if isinstance(raw_content, str):
            # 字符串可能是 JSON 字符串，尝试解析后递归标准化
            try:
                parsed = json.loads(raw_content)
                return self._normalize_diagram_content(parsed, request)
            except Exception:
                # 非 JSON 字符串直接作为 mermaid source 使用
                return {
                    "diagram_type": request.agent_configs.diagram.diagram_type,
                    "render_format": "mermaid",
                    "source": raw_content,
                    "description": "知识图解",
                }
        # 完全无法解析时返回默认空结构
        return {
            "diagram_type": request.agent_configs.diagram.diagram_type,
            "render_format": "mermaid",
            "source": "",
            "description": "知识图解",
        }

    def _normalize_code_content(self, raw_content: Any, request: ResourceGenerationRequest) -> dict[str, Any]:
        """标准化 code 内容为统一格式 {language, code, explanation, ...}。"""
        if isinstance(raw_content, dict):
            # 已经是字典格式，直接作为标准化结果返回
            return raw_content
        if isinstance(raw_content, str):
            # 尝试解析 JSON 字符串，若解析成功且为字典则直接使用
            try:
                parsed = json.loads(raw_content)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
            # 纯文本字符串作为 code 字段，其余字段使用默认值
            return {
                "language": request.agent_configs.code.programming_language,
                "code": raw_content,
                "explanation": "代码实操案例",
                "input_example": "",
                "output_example": "",
                "complexity": {"time": "", "space": ""},
                "run_steps": [],
                "debug_tips": [],
                "exercises": [],
            }
        # 不支持的格式返回空默认结构
        return {
            "language": request.agent_configs.code.programming_language,
            "code": "",
            "explanation": "",
            "input_example": "",
            "output_example": "",
            "complexity": {"time": "", "space": ""},
            "run_steps": [],
            "debug_tips": [],
            "exercises": [],
        }

    def _normalize_reading_content(self, raw_content: Any) -> dict[str, Any]:
        """标准化 reading 内容为统一格式 {items: [...]}。"""
        if isinstance(raw_content, dict):
            # 已有 items 字段的直接返回，否则包裹为单条 item
            if "items" in raw_content:
                return raw_content
            return {"items": [raw_content]}
        if isinstance(raw_content, str):
            # 字符串可能是 JSON，尝试解析后递归标准化
            try:
                parsed = json.loads(raw_content)
                return self._normalize_reading_content(parsed)
            except Exception:
                # 纯文本视为单条阅读推荐的 description
                return {"items": [{"title": "拓展阅读", "type": "article", "description": raw_content, "reason": "", "difficulty": "medium", "url": ""}]}
        # 兜底返回空列表
        return {"items": []}
