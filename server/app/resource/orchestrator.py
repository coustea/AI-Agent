"""
资源生成编排器。

实现完整的资源生成工作流：
1. load_profile - 加载学习者画像
2. create_task - 创建任务记录
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
from app.resource.schemas import (
    AgentSelection,
    GeneratedResourceItem,
    ResourceAgentId,
    ResourceBundle,
    ResourceGenerationRequest,
    ReviewIssue,
    ReviewResult,
    StudyPathStep,
    WorkerState,
)
from app.resource.utils import load_profile_snapshot
from app.resource.worker_agents import (
    CodeAgent,
    ContentAgent,
    DiagramAgent,
    MindmapAgent,
    QuizAgent,
    ReadingAgent,
)

logger = get_logger(__name__)

# Agent 依赖关系（仅用于同层排序，不阻塞执行）
AGENT_DEPENDENCIES: dict[str, list[str]] = {
    "content": [],
    "mindmap": ["content"],
    "diagram": ["content"],
    "quiz": ["content"],
    "code": ["content"],
    "reading": ["content"],
}

# 学习路径默认顺序
STUDY_PATH_ORDER = ["content", "diagram", "mindmap", "code", "quiz", "reading"]

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
    """工作流规划 Agent。

    职责：
    1. 读取 ResourceGenerationRequest
    2. 根据 selected_agents.enabled=true 得到目标 Agent
    3. 根据 registry 中的依赖关系和 priority 生成 workflow_plan
    4. 按层规划执行
    """

    def build_workflow_plan(self, request: ResourceGenerationRequest) -> list[dict[str, Any]]:
        """构建工作流计划。

        返回结构：
        [
            {
                "agent_id": "content",
                "agent_name": "ContentAgent",
                "resource_type": "content",
                "layer": 0,
                "depends_on": [],
                "reason": "先生成课程讲解文档，为其他资源提供基础上下文",
                "visible": true
            },
            ...
        ]
        """
        selected_agents = request.selected_agents
        enabled = [x for x in selected_agents if x.enabled]
        if not enabled:
            return []

        priority_map = {item.agent_id.value: item.priority for item in enabled}
        selected_order = request.enabled_agent_ids()
        selected_set = set(selected_order)
        content_enabled = "content" in selected_set

        layers: dict[int, list[str]] = {0: [], 1: [], 2: []}
        if content_enabled:
            if "content" in selected_set:
                layers[0].append("content")
            for agent_id in ("diagram", "mindmap"):
                if agent_id in selected_set:
                    layers[1].append(agent_id)
            for agent_id in ("code", "quiz", "reading"):
                if agent_id in selected_set:
                    layers[2].append(agent_id)
        else:
            # 没有 content 时，所有 Agent 在同一层并行执行
            layers = {0: [agent_id for agent_id in selected_order if agent_id != "content"]}

        for agent_ids in layers.values():
            agent_ids.sort(key=lambda agent_id: priority_map.get(agent_id, 0))

        workflow_plan: list[dict[str, Any]] = []
        for layer_idx, agent_ids in sorted(layers.items()):
            for agent_id in agent_ids:
                entry = get_agent_entry(agent_id)
                if entry is None:
                    continue
                depends_on = [dep for dep in entry.dependencies if dep in selected_set]
                workflow_plan.append(
                    {
                        "agent_id": agent_id,
                        "agent_name": entry.agent_class.__name__,
                        "resource_type": agent_id,
                        "layer": layer_idx,
                        "depends_on": depends_on,
                        "reason": self._get_agent_reason(agent_id),
                        "visible": True,
                    }
                )

        return workflow_plan

    def _get_agent_reason(self, agent_id: str) -> str:
        """获取 Agent 执行原因。"""
        reasons = {
            "content": "先生成课程讲解文档，为其他资源提供基础上下文",
            "diagram": "基于讲解内容生成知识图解，帮助理解复杂概念",
            "mindmap": "基于讲解内容生成思维导图，梳理知识结构",
            "code": "基于讲解内容生成代码实操案例，加深理解",
            "quiz": "基于讲解内容生成练习题，检验学习效果",
            "reading": "基于讲解内容推荐拓展阅读，扩展知识面",
        }
        return reasons.get(agent_id, "基于学习任务与个性化配置生成资源")


class ReviewerAgent:
    """资源审查 Agent。

    职责：
    1. 检查资源完整性
    2. 检查资源质量
    3. 生成审查报告
    """

    def review(
        self,
        request: ResourceGenerationRequest,
        resources: list[GeneratedResourceItem],
        failed_agents: list[str],
        errors: list[str],
    ) -> ReviewResult:
        """执行资源审查。"""
        issues: list[ReviewIssue] = []
        suggestions: list[str] = []
        selected_agents = request.enabled_agent_ids()

        # 检查资源是否为空
        if not resources:
            issues.append(ReviewIssue(
                level="error",
                message="至少应生成一个资源",
                suggestion="请检查 Agent 执行日志",
            ))
            return ReviewResult(passed=False, score=0, issues=issues, suggestions=suggestions)

        # 构建资源映射
        resource_map = {res.type.value: res for res in resources}

        # 检查每个启用的 Agent 是否有结果
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
            elif isinstance(content, str):
                if not content:
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

        # 计算评分
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
    """资源包组装 Agent。

    职责：
    1. 生成 ResourceBundle
    2. 生成资源包标题
    3. 生成推荐学习路径
    4. 整合 resources
    5. 附加 review_result
    6. 计算最终 status
    """

    def assemble(
        self,
        task_id: str,
        resource_id: str,
        request: ResourceGenerationRequest,
        resources: list[GeneratedResourceItem],
        review_result: ReviewResult,
        failed_agents: list[str],
    ) -> ResourceBundle:
        """组装资源包。"""
        # 生成标题
        title = request.output_options.final_bundle_title
        if not title:
            course = request.task.course
            topic = request.task.topic
            title = f"{course} - {topic} 个性化学习资源包"

        # 生成学习路径
        study_path: list[StudyPathStep] = []
        if request.output_options.include_study_path:
            study_path = self._build_study_path(resources)

        # 计算状态
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
            task=request.task,
            personalization=request.personalization,
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
    """资源生成工作流。"""

    def __init__(self, emitter: AgentEventEmitter, resource_store: Any):
        self.emitter = emitter
        self.resource_store = resource_store
        self.master_agent = MasterAgent()
        self.reviewer_agent = ReviewerAgent()
        self.assembler_agent = AssemblerAgent()

    async def run(self, user_id: int, request: ResourceGenerationRequest) -> dict[str, Any]:
        """执行资源生成工作流。"""
        ensure_initialized()
        enabled_agent_ids = request.enabled_agent_ids()
        task_id = str(uuid4())
        self.emitter.bind_task(task_id)

        # 1. workflow created
        await self.emitter.emit_workflow(
            stage="created",
            status="pending",
            message="资源生成任务已创建",
            payload={"selected_agents": enabled_agent_ids},
            progress=0,
        )

        try:
            # 2. load_profile
            snapshot = await load_profile_snapshot(user_id)
            learner_profile = snapshot.as_agent_profile()

            # 3. create_task
            resource_record = await self.resource_store.create_resource(
                user_id=user_id,
                request=request,
            )
            resource_id = resource_record.id

            # 4. plan_workflow
            await self.emitter.emit_workflow(
                stage="planning",
                status="running",
                message="开始规划多智能体工作流",
                progress=5,
            )

            workflow_plan = self.master_agent.build_workflow_plan(request)

            await self.emitter.emit_workflow(
                stage="planning",
                status="success",
                message="工作流规划完成",
                payload={"workflow_plan": workflow_plan},
                progress=10,
            )

            # 5. execute_layer
            agent_context = {
                "task": request.task.model_dump(),
                "personalization": request.personalization.model_dump(),
                "agent_configs": request.agent_configs.model_dump(),
                "selected_agents": enabled_agent_ids,
                "learner_profile": learner_profile,
            }

            raw_results: dict[str, dict[str, Any]] = {}
            resources: list[GeneratedResourceItem] = []
            failed_agents: list[str] = []
            errors: list[str] = []
            upstream_results: dict[str, Any] = {}

            # 按层执行
            layers = self._group_by_layer(workflow_plan)
            total_agents = len(workflow_plan)
            completed_count = 0

            for layer_idx, layer_agents in layers.items():
                # 过滤出本层可以执行的 Agent（依赖满足或依赖不在选中列表中）
                ready_plans: list[dict[str, Any]] = []
                for plan in layer_agents:
                    selected_dependencies = [dep for dep in plan.get("depends_on", []) if dep in enabled_agent_ids]
                    blocking_dependencies = [
                        dep for dep in selected_dependencies
                        if dep not in upstream_results and dep not in failed_agents
                    ]
                    if blocking_dependencies:
                        continue
                    ready_plans.append(plan)

                async def run_plan(plan: dict[str, Any]) -> tuple[str, dict[str, Any], list[str]]:
                    agent_id = plan["agent_id"]
                    dependencies = [dep for dep in plan.get("depends_on", []) if dep in enabled_agent_ids]
                    available_dependencies = [dep for dep in dependencies if dep in upstream_results]
                    await self.emitter.emit_agent(
                        agent=agent_id,
                        status="running",
                        message=f"{agent_id} 正在生成",
                        payload={"depends_on": available_dependencies, "layer": layer_idx},
                        progress=min(10 + int(completed_count / max(total_agents, 1) * 75), 85),
                    )
                    result = await self._run_agent(
                        user_id=user_id,
                        resource_id=resource_id,
                        agent_id=agent_id,
                        request=request,
                        agent_context=agent_context,
                        workflow_plan=workflow_plan,
                        upstream_results=upstream_results,
                        dependencies=dependencies,
                        layer_index=layer_idx,
                    )
                    return agent_id, result, available_dependencies

                layer_results = await asyncio.gather(
                    *(run_plan(plan) for plan in ready_plans),
                    return_exceptions=True,
                )

                for item_result in layer_results:
                    completed_count += 1
                    if isinstance(item_result, Exception):
                        message = str(item_result)
                        errors.append(message)
                        await self.emitter.emit_error(stage="generating", message=message)
                        continue

                    agent_id, result, depends_on = item_result
                    raw_results[agent_id] = result

                    if result.get("success"):
                        resource_item = self._build_resource_item(
                            agent_id=agent_id,
                            result=result,
                            depends_on=depends_on,
                            request=request,
                        )
                        try:
                            saved_item = await self.resource_store.save_resource_item(
                                resource_id=resource_id,
                                user_id=user_id,
                                item=resource_item,
                            )
                        except Exception as save_exc:
                            logger.exception("[ResourceWorkflow] 资源项保存失败: agent=%s", agent_id)
                            failed_agents.append(agent_id)
                            message = f"{agent_id} 数据库保存失败: {save_exc}"
                            errors.append(message)
                            await self.emitter.emit_agent(
                                agent=agent_id,
                                status="failed",
                                message=message,
                                payload={"error": str(save_exc), "stage": "save_resource_item"},
                            )
                            await self.emitter.emit_error(
                                stage="generating",
                                agent=agent_id,
                                message=message,
                            )
                            continue

                        if saved_item.id is not None:
                            resource_item.id = str(saved_item.id)
                        resources.append(resource_item)
                        upstream_results[agent_id] = resource_item.model_dump(mode="json")
                        await self.emitter.emit_agent(
                            agent=agent_id,
                            status="success",
                            message=f"{agent_id} 生成完成",
                            payload={"resource": resource_item.model_dump(mode="json")},
                            progress=min(10 + int(completed_count / max(total_agents, 1) * 75), 90),
                        )
                        await self.emitter.emit_resource(
                            agent=agent_id,
                            resource=resource_item,
                            message=f"{agent_id} 生成完成",
                            payload={"db_item_id": saved_item.id},
                            progress=min(10 + int(completed_count / max(total_agents, 1) * 75), 90),
                        )
                    else:
                        failed_agents.append(agent_id)
                        message = f"{agent_id} 生成失败: {result.get('error', 'unknown error')}"
                        errors.append(message)
                        await self.emitter.emit_agent(
                            agent=agent_id,
                            status="failed",
                            message=message,
                            payload={"error": result.get("error")},
                        )
                        await self.emitter.emit_error(
                            stage="generating",
                            agent=agent_id,
                            message=message,
                        )

            # 6. review_resources
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
                resources=resources,
                failed_agents=failed_agents,
                errors=errors,
            )

            await self.emitter.emit_review(
                review_result=review_result,
                progress=95,
            )

            # 7. assemble_bundle
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
                resources=resources,
                review_result=review_result,
                failed_agents=failed_agents,
            )

            await self.resource_store.update_resource_status(
                resource_id=resource_id,
                status=bundle.status,
            )

            # emit bundle success
            await self.emitter.emit_bundle(
                bundle=bundle,
                progress=100,
            )

            # 8. finalize
            await self.emitter.emit_done(bundle=bundle)

            return {"success": bundle.status != "failed", "results": raw_results, "bundle": bundle.model_dump(mode="json")}

        except Exception as exc:
            logger.exception("[ResourceWorkflow] 执行失败")
            await self.emitter.emit_error(message=str(exc))
            return {"success": False, "results": {}, "error": str(exc)}

    def _group_by_layer(self, workflow_plan: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
        """按层分组。"""
        layers: dict[int, list[dict[str, Any]]] = {}
        for plan in workflow_plan:
            layer = plan.get("layer", 0)
            if layer not in layers:
                layers[layer] = []
            layers[layer].append(plan)
        return layers

    async def _run_agent(
        self,
        *,
        user_id: int,
        resource_id: int,
        agent_id: str,
        request: ResourceGenerationRequest,
        agent_context: dict[str, Any],
        workflow_plan: list[dict[str, Any]],
        upstream_results: dict[str, Any],
        dependencies: list[str],
        layer_index: int,
    ) -> dict[str, Any]:
        """执行单个 Agent。"""
        agent_cls = AGENT_CLASS_MAP.get(agent_id)
        if agent_cls is None:
            return {"success": False, "error": f"Unknown agent: {agent_id}"}

        worker = agent_cls(user_id, resource_id, emitter=self.emitter)

        # 构建任务负载
        task_payload = {
            "course": request.task.course,
            "chapter": request.task.chapter,
            "topic": request.task.topic,
            "weak_points": request.task.weak_points,
            "learning_goal": request.task.learning_goal.value,
            "extra_requirement": request.task.extra_requirement,
            "resource_generation": {
                "task": request.task.model_dump(),
                "personalization": request.personalization.model_dump(),
                "agent_context": agent_context,
                "workflow_plan": workflow_plan,
                "upstream_results": upstream_results,
            },
        }

        # 获取 Agent 专属配置
        agent_config = request.agent_configs.model_dump().get(agent_id, {})

        # 构建 WorkerState
        state = WorkerState(
            user_id=user_id,
            resource_id=resource_id,
            agent_name=agent_id,
            task=task_payload,
            learner_profile=agent_context.get("learner_profile", {}),
            personalization=request.personalization.model_dump(),
            agent_config=agent_config,
            workflow_plan=workflow_plan,
            dependencies=dependencies,
            upstream_results=upstream_results,
            dependency_reports={},
            layer_index=layer_index,
        )

        result = await worker.run(state)
        return result.model_dump() if hasattr(result, "model_dump") else dict(result)

    def _build_resource_item(
        self,
        *,
        agent_id: str,
        result: dict[str, Any],
        depends_on: list[str],
        request: ResourceGenerationRequest,
    ) -> GeneratedResourceItem:
        """构建资源项。"""
        raw_content = result.get("content", "")
        parsed_content: Any = raw_content
        fmt = self._infer_format(agent_id, result)

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
            title=result.get("title") or f"{request.task.topic} - {agent_id}",
            format=fmt,
            content=parsed_content,
            summary=result.get("summary") or summary,
            execution_report=result.get("execution_report"),
            metadata=metadata,
        )

    def _infer_format(self, agent_id: str, result: dict[str, Any]) -> str:
        """推断资源格式。"""
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
