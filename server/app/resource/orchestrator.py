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

from app.infra.logging import get_logger
from app.resource.events import AgentEventEmitter
from app.resource.registry import ensure_initialized, get_agent_entry
from app.resource.utils import load_profile_snapshot
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


AGENT_DEPENDENCIES: dict[str, list[str]] = {
    "content": [],
    "mindmap": [],
    "diagram": [],
    "quiz": ["content", "code"],
    "code": [],
    "reading": [],
}

# 学习路径默认顺序（按 Layer 0 → Layer 1 → Layer 2 排列）
STUDY_PATH_ORDER = ["content", "mindmap", "diagram", "code", "quiz", "reading"]

# 学习路径预计时间（分钟）
STUDY_PATH_ESTIMATED_TIME = {
    "content": 8,
    "diagram": 5,
    "mindmap": 5,
    "code": 12,
    "quiz": 15,
    "reading": 20,
}

# Agent 类映射
AGENT_CLASS_MAP = {
    "content": ContentAgent,
    "mindmap": MindmapAgent,
    "diagram": DiagramAgent,
    "quiz": QuizAgent,
    "reading": ReadingAgent,
    "code": CodeAgent,
}


class MasterAgent:
    """工作流动态规划 Agent。使用 LLM 每层执行前重新规划。"""

    LAYER_AGENTS: dict[int, list[str]] = {
        0: ["content", "mindmap", "diagram"],
        1: ["code", "reading"],
        2: ["quiz"],
    }

    def __init__(self) -> None:
        from app.infra.llm import get_llm_manager
        self.llm = get_llm_manager().get_model("spark_max")

    async def plan_layer(self, context: PlanningContext) -> LayerPlan:
        """根据当前上下文规划下一层执行计划。"""
        layer_agents = self.LAYER_AGENTS.get(context.layer, [])
        candidates = [a for a in layer_agents if a in context.user_explicit_selection]

        if not candidates:
            return LayerPlan(layer=context.layer, agents=[], reasoning="本层无待执行 Agent")

        agent_tasks = await self._generate_agent_tasks(
            context=context,
            candidates=candidates,
            explicit_set=set(context.user_explicit_selection),
        )

        return LayerPlan(
            layer=context.layer,
            agents=agent_tasks,
            reasoning=f"本层执行 {len(agent_tasks)} 个 Agent",
        )

    async def _generate_agent_tasks(
        self,
        context: PlanningContext,
        candidates: list[str],
        explicit_set: set[str],
    ) -> list[AgentTask]:
        """确定性生成任务描述。"""
        return self._default_agent_tasks(candidates, explicit_set, context)

    def _default_agent_tasks(
        self,
        candidates: list[str],
        explicit_set: set[str],
        context: PlanningContext,
    ) -> list[AgentTask]:
        """默认 Agent 任务规划。"""
        learning_need = context.question.learning_need

        tasks = []
        for i, agent_id in enumerate(candidates):
            agent_config = context.question.agent_configs.model_dump().get(agent_id, {})
            task_desc = self._build_default_task_description(agent_id, learning_need)

            tasks.append(AgentTask(
                agent_id=agent_id,
                task_description=task_desc,
                depends_on=[],
                is_explicit=agent_id in explicit_set,
                priority=i,
                config=agent_config,
            ))

        return tasks

    def _build_default_task_description(
        self,
        agent_id: str,
        learning_need: str,
    ) -> str:
        """构建默认任务描述。"""
        base_desc = f"根据用户学习需求生成{self._get_agent_name(agent_id)}。"

        if learning_need:
            base_desc = f"根据用户需求「{learning_need[:100]}」生成{self._get_agent_name(agent_id)}。"

        return base_desc

    def _get_agent_name(self, agent_id: str) -> str:
        """获取 Agent 中文名称。"""
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

        # 空资源检查
        if not resources:
            issues.append(ReviewIssue(
                level="error",
                message="至少应生成一个资源",
                suggestion="请检查 Agent 执行日志",
            ))
            return ReviewResult(passed=False, score=0, issues=issues, suggestions=suggestions)

        # 构建资源类型到资源的映射
        resource_map = {res.type.value: res for res in resources}

        # 检查启用但未产出的 Agent
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

        # 计算评分：基于成功数、错误数、警告数
        success_count = len(resources)
        total_count = len(selected_agents)
        error_count = sum(1 for i in issues if i.level == "error")
        warning_count = sum(1 for i in issues if i.level == "warning")

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

        # 生成建议
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
        # 生成标题（优先使用请求中的标题）
        title = request.output_options.final_bundle_title
        if not title:
            title = "个性化学习资源包"

        # 构建学习路径（按固定顺序）
        study_path: list[StudyPathStep] = []
        if request.output_options.include_study_path:
            study_path = self._build_study_path(resources)

        # 计算最终状态：全部成功/部分失败/全部失败
        if not resources:
            status = "failed"
        elif failed_agents:
            status = "partial_completed"
        else:
            status = "completed"

        # 转换 selected_agents
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
        self.emitter = emitter
        self.resource_store = resource_store
        self.master_agent = MasterAgent()
        self.reviewer_agent = ReviewerAgent()
        self.assembler_agent = AssemblerAgent()

    async def run(self, user_id: int, request: ResourceGenerationRequest) -> dict[str, Any]:
        """执行资源生成工作流，每层动态规划。"""
        ensure_initialized()
        user_explicit_selection = request.enabled_agent_ids()
        task_id = str(uuid4())
        self.emitter.bind_task(task_id)

        await self.emitter.emit_workflow(
            stage="created",
            status="pending",
            message="资源生成任务已创建",
            payload={"selected_agents": user_explicit_selection},
            progress=0,
        )

        try:
            resource_record = await self.resource_store.create_resource(
                user_id=user_id,
                request=request,
            )
            resource_id = resource_record.id
            snapshot = await load_profile_snapshot(user_id)
            learner_profile = snapshot.as_agent_profile()

            await self.emitter.emit_workflow(
                stage="planning",
                status="running",
                message="开始规划多智能体工作流",
                progress=5,
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
            errors: list[str] = []
            content_markdown: str | None = None
            code_content: Any = None
            total_layers = 3
            completed_layers = 0

            for layer in range(total_layers):
                planning_context = PlanningContext(
                    layer=layer,
                    question=request,
                    user_explicit_selection=user_explicit_selection,
                    implicit_dependencies=[],
                    upstream_results={},
                    upstream_reports={},
                )

                layer_plan = await self.master_agent.plan_layer(planning_context)

                await self.emitter.emit_workflow(
                    stage=f"planning_layer_{layer}",
                    status="success",
                    message=f"Layer {layer} 规划完成: {len(layer_plan.agents)} 个 Agent",
                    payload={"layer_plan": layer_plan.model_dump(mode="json")},
                    progress=10 + int(completed_layers / total_layers * 5),
                )

                if not layer_plan.agents:
                    completed_layers += 1
                    continue

                layer_tasks = []
                for agent_task in layer_plan.agents:
                    layer_tasks.append(
                        self._execute_agent_task(
                            agent_task=agent_task,
                            user_id=user_id,
                            resource_id=resource_id,
                            request=request,
                            agent_context=agent_context,
                            upstream_results=raw_results,
                            layer_index=layer,
                        )
                    )

                layer_results = await asyncio.gather(*layer_tasks, return_exceptions=True)

                content_markdown, code_content = await self._finalize_layer_results(
                    layer_results=layer_results,
                    resource_id=resource_id,
                    user_id=user_id,
                    request=request,
                    raw_results=raw_results,
                    all_resources=all_resources,
                    content_markdown=content_markdown,
                    code_content=code_content,
                    failed_agents=failed_agents,
                    errors=errors,
                )

                completed_layers += 1
                progress = 10 + int(completed_layers / total_layers * 80)
                await self.emitter.emit_workflow(
                    stage=f"layer_{layer}_done",
                    status="success",
                    message=f"Layer {layer} 执行完成",
                    progress=min(progress, 90),
                )

            explicit_resources = [
                r for r in all_resources
                if r.type.value in user_explicit_selection
            ]

            await self.emitter.emit_event(
                event_type="review",
                stage="reviewing",
                status="running",
                message="开始资源检查",
                agent="reviewer",
                progress=92,
            )

            review_result = self.reviewer_agent.review(
                request=request,
                resources=explicit_resources,
                failed_agents=failed_agents,
                errors=errors,
            )

            await self.emitter.emit_review(review_result=review_result, progress=95)

            await self.emitter.emit_event(
                event_type="bundle",
                stage="assembling",
                status="running",
                message="开始组装资源包",
                agent="assembler",
                progress=97,
            )

            bundle = self.assembler_agent.assemble(
                task_id=task_id,
                resource_id=str(resource_id),
                request=request,
                resources=explicit_resources,
                review_result=review_result,
                failed_agents=failed_agents,
            )

            await self.resource_store.update_resource_status(
                resource_id=resource_id,
                status=bundle.status,
            )

            await self.emitter.emit_bundle(bundle=bundle, progress=100)
            await self.emitter.emit_done(bundle=bundle)

            return {"success": bundle.status != "failed", "results": raw_results, "bundle": bundle.model_dump(mode="json")}

        except Exception as exc:
            logger.exception("[ResourceWorkflow] 执行失败")
            await self.emitter.emit_error(message=str(exc))
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
        layer_index: int,
    ) -> tuple[str, dict[str, Any], bool]:
        """执行单个 AgentTask 并返回结果。"""
        agent_id = agent_task.agent_id
        agent_cls = AGENT_CLASS_MAP.get(agent_id)
        if agent_cls is None:
            return agent_id, {"success": False, "error": f"Unknown agent: {agent_id}"}, agent_task.is_explicit

        await self.emitter.emit_agent(
            agent=agent_id,
            status="running",
            message=f"{agent_id} 正在生成",
            payload={"task_description": agent_task.task_description[:100], "layer": layer_index},
        )

        worker = agent_cls(user_id, resource_id, emitter=self.emitter)

        task_payload = {
            "learning_need": request.learning_need,
            "task_description": agent_task.task_description,
        }
        dependency_reports = {
            dep: upstream_results[dep].get("execution_report") or upstream_results[dep].get("summary", "")
            for dep in AGENT_DEPENDENCIES.get(agent_id, [])
            if dep in upstream_results
        }

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
        )

        result = await worker.run(state)
        return agent_id, result.model_dump() if hasattr(result, "model_dump") else dict(result), agent_task.is_explicit

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
        raw_results: dict[str, dict[str, Any]] | None = None,
    ) -> tuple[str | None, Any]:
        """并发保存同一层成功产物，并收集失败信息。"""
        save_inputs = []

        for item_result in layer_results:
            if isinstance(item_result, Exception):
                errors.append(str(item_result))
                await self.emitter.emit_error(stage="generating", message=str(item_result))
                continue

            agent_id, result, is_explicit = item_result
            if raw_results is not None:
                raw_results[agent_id] = result

            if result.get("success"):
                save_inputs.append(
                    (
                        agent_id,
                        result,
                        is_explicit,
                    )
                )
                continue

            failed_agents.append(agent_id)
            errors.append(f"{agent_id} 生成失败: {result.get('error', 'unknown')}")
            await self.emitter.emit_agent(
                agent=agent_id,
                status="failed",
                message=f"{agent_id} 生成失败",
            )

        saved_results = []
        for agent_id, result, is_explicit in save_inputs:
            try:
                saved_item = await self._save_successful_agent_result(
                    agent_id=agent_id,
                    result=result,
                    is_explicit=is_explicit,
                    resource_id=resource_id,
                    user_id=user_id,
                    request=request,
                )
                saved_results.append((agent_id, saved_item, None))
            except Exception as exc:
                saved_results.append((agent_id, None, str(exc)))

        for agent_id, resource_item, error in saved_results:
            if error:
                errors.append(error)
                await self.emitter.emit_error(stage="saving", message=error)
                continue
            if resource_item is None:
                failed_agents.append(agent_id)
                continue
            all_resources.append(resource_item)
            # 提取 content 和 code 的结果供 quiz 使用
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
        resource_id: int,
        user_id: int,
        request: ResourceGenerationRequest,
    ) -> GeneratedResourceItem | None:
        """保存单个成功 Agent 的产物并发出完成事件。"""
        resource_item = self._build_resource_item(
            agent_id=agent_id,
            result=result,
            depends_on=AGENT_DEPENDENCIES.get(agent_id, []),
            request=request,
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
                message=f"{agent_id} 生成完成",
                payload={"resource": resource_item.model_dump(mode="json"), "is_explicit": is_explicit},
            )
            await self.emitter.emit_resource(
                agent=agent_id,
                resource=resource_item,
                message=f"{agent_id} 生成完成",
            )
            return resource_item
        except Exception as save_exc:
            await self.emitter.emit_agent(
                agent=agent_id,
                status="failed",
                message=f"{agent_id} 数据库保存失败",
            )
            raise RuntimeError(f"{agent_id} 保存失败: {save_exc}") from save_exc

    def _build_resource_item(
        self,
        *,
        agent_id: str,
        result: dict[str, Any],
        depends_on: list[str],
        request: ResourceGenerationRequest,
    ) -> GeneratedResourceItem:
        """构建资源项，标准化不同类型的内容格式。"""
        raw_content = result.get("content", "")
        parsed_content: Any = raw_content
        fmt = self._infer_format(agent_id, result)

        # 根据类型解析和标准化内容
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
            try:
                parsed_content = json.loads(raw_content) if isinstance(raw_content, str) else raw_content
            except Exception:
                parsed_content = {"raw": raw_content}

        # 构建元数据
        summary = f"{agent_id} 资源已生成"
        metadata = dict(result.get("metadata") or {})
        metadata.update({
            "agent": f"{agent_id.capitalize()}Agent",
            "depends_on": depends_on,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "config": request.agent_configs.model_dump().get(agent_id, {}),
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

    def _infer_format(self, agent_id: str, result: dict[str, Any]) -> str:
        """根据 Agent 类型和结果推断资源格式。"""
        if agent_id in {"content", "mindmap"}:
            return "markdown"
        if agent_id == "diagram":
            return "mermaid"
        if agent_id in {"quiz", "reading", "code"}:
            return "json"
        # 根据 file_type 推断
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
            if "source" in raw_content:
                return raw_content
            render = raw_content.get("render")
            if isinstance(render, dict) and render.get("source"):
                return {
                    "diagram_type": raw_content.get("diagram_type") or raw_content.get("type") or request.agent_configs.diagram.diagram_type,
                    "render_format": render.get("engine", "mermaid"),
                    "source": render.get("source", ""),
                    "description": raw_content.get("description") or raw_content.get("summary", "知识图解"),
                }
        if isinstance(raw_content, str):
            try:
                parsed = json.loads(raw_content)
                return self._normalize_diagram_content(parsed, request)
            except Exception:
                return {
                    "diagram_type": request.agent_configs.diagram.diagram_type,
                    "render_format": "mermaid",
                    "source": raw_content,
                    "description": "知识图解",
                }
        return {
            "diagram_type": request.agent_configs.diagram.diagram_type,
            "render_format": "mermaid",
            "source": "",
            "description": "知识图解",
        }

    def _normalize_code_content(self, raw_content: Any, request: ResourceGenerationRequest) -> dict[str, Any]:
        """标准化 code 内容为统一格式 {language, code, explanation, ...}。"""
        if isinstance(raw_content, dict):
            return raw_content
        if isinstance(raw_content, str):
            try:
                parsed = json.loads(raw_content)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
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
            if "items" in raw_content:
                return raw_content
            return {"items": [raw_content]}
        if isinstance(raw_content, str):
            try:
                parsed = json.loads(raw_content)
                return self._normalize_reading_content(parsed)
            except Exception:
                return {"items": [{"title": "拓展阅读", "type": "article", "description": raw_content, "reason": "", "difficulty": "medium", "url": ""}]}
        return {"items": []}
