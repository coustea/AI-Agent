"""路径规划服务 — 路径生成、节点工作区、测验、评估一体化。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import ProgrammingError
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.evaluation.request import LearningEventCreate
from app.evaluation.response import LearningEventItem
from app.evaluation.service import EvaluationService, bg_apply_profile_update_from_learning_event, build_summary_from_events
from app.infra.logging import get_logger
from app.infra.models import (
    LearningEvent,
    LearningPath,
    LearningSession,
    PathNode,
    PathNodeQuestion,
    PathNodeResource,
    PathNodeTutorial,
)
from app.profile.service import get_profile_service
from app.path.planner import PathPlannerAgent, repair_generated_plan_from_macro_stages
from app.path.node_learning import NodeLearningAgent
from app.path.events import PathEvent, path_event_bus
from app.path.schemas import (
    AgentLearningPathPlan,
    AuxiliaryResourceRequest,
    CreateLearningPathRequest,
    LearningPathHistoryItem,
    LearningPathNodeDTO,
    LearningPathNodeWorkspaceResponse,
    LearningPathOverviewResponse,
    LearningPathQuestionDTO,
    LearningPathResourceDTO,
    LearningPathTutorialDTO,
    LearningSignalSnapshot,
    PathLearningEvaluationResponse,
    PathQuizRoundResponse,
    PathQuizSubmitRequest,
    PathQuizSubmitResponse,
)
from app.path.validation import normalize_path_plan, validate_path_plan
from app.resource.agents import AGENT_REGISTRY
from app.resource.schemas import NodeInput

logger = get_logger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

PASS_SCORE = 3
QUIZ_SIZE = 5
AUX_RESOURCE_TYPES = {"content", "mindmap", "code", "reading", "quiz", "ppt"}
ACTIVE_NODE_STATUSES = {"available", "in_progress", "remediation", "reinforced"}
STARTED_NODE_STATUSES = {"in_progress", "remediation", "reinforced"}
COMPLETED_NODE_STATUSES = {"completed", "completed_with_gaps"}
ACCESSIBLE_NODE_STATUSES = ACTIVE_NODE_STATUSES | COMPLETED_NODE_STATUSES
DEEP_LEARNING_NODE_STATUSES = STARTED_NODE_STATUSES | COMPLETED_NODE_STATUSES


class PathService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.profile_builder = get_profile_service()
        self.path_planner = PathPlannerAgent()
        self.node_learning_agent = NodeLearningAgent()
        self.evaluation_service = EvaluationService()

    # ── 路径规划 ────────────────────────────────────────────────────────────

    async def init_path_task(self, user_id: int, request: CreateLearningPathRequest) -> int:
        await self._archive_active_paths(user_id, request.module)
        path = LearningPath(
            user_id=user_id,
            module=request.module,
            title=request.topic or "学习路径",
            goal=request.goal,
            topic=request.topic or None,
            overall_progress=0,
            eta_days=0,
            confidence=0,
            status="generating",
            stages_json=[],
        )
        self.session.add(path)
        await self.session.commit()
        await self.session.refresh(path)
        return path.id

    async def complete_path_generation(
        self,
        path_id: int,
        user_id: int,
        request: CreateLearningPathRequest,
        plan: AgentLearningPathPlan,
    ) -> None:
        path = await self.session.get(LearningPath, path_id)
        if not path:
            return
        plan = normalize_path_plan(plan)
        validate_path_plan(plan)

        path.eta_days = plan.eta_days
        path.confidence = plan.confidence
        path.status = "active"
        path.title = plan.title
        path.stages_json = [self._stage_to_dict(stage) for stage in plan.stages]

        completed_keys: set[str] = set()
        nodes: list[PathNode] = []
        for index, node_data in enumerate(plan.nodes):
            prerequisites = list(getattr(node_data, "prerequisites", []) or [])
            status = "available" if not prerequisites or set(prerequisites).issubset(completed_keys) else "locked"
            node = PathNode(
                path_id=path.id,
                user_id=user_id,
                node_id=node_data.node_id,
                stage_id=node_data.stage_id,
                title=node_data.title,
                status=status,
                priority=index + 1,
                prerequisites=prerequisites,
                resource_policy=node_data.resource_policy.model_dump(mode="json")
                if node_data.resource_policy
                else None,
                mastery_target=getattr(node_data, "mastery_target", None),
                estimated_minutes=getattr(node_data, "estimated_minutes", None),
                difficulty=getattr(node_data, "difficulty", None),
                recommendation_reason=getattr(node_data, "recommendation_reason", None),
            )
            self.session.add(node)
            nodes.append(node)
        if nodes:
            path.current_node_key = nodes[0].node_id
        await self.session.commit()

    async def run_generation(self, path_id: int, user_id: int, request: CreateLearningPathRequest) -> None:
        """完整生成管线：画像获取 → 规划 → 修复 → 验证 → 持久化 → 事件发布。"""
        profile = await self._get_profile_dict(user_id)
        profile_md = await self.get_user_learning_profile(user_id)

        async def progress_cb(status: str, progress: int, message: str) -> None:
            await path_event_bus.publish(path_id, PathEvent(
                event_type="path.step", path_id=path_id, status="generating",
                message=message, progress=progress,
            ))

        try:
            await path_event_bus.publish(path_id, PathEvent(
                event_type="path.step", path_id=path_id, status="generating",
                message="正在初始化路径推演引擎", progress=10,
            ))

            plan = await self.path_planner.generate_plan(
                request, profile, progress_callback=progress_cb, profile_markdown=profile_md,
            )

            await path_event_bus.publish(path_id, PathEvent(
                event_type="path.step", path_id=path_id, status="generating",
                message="正在生成节点结构", progress=85,
            ))

            plan = repair_generated_plan_from_macro_stages(
                plan=plan,
                macro_stages=list(getattr(plan, "stages", []) or []),
                request=request,
            )

            await self.complete_path_generation(path_id, user_id, request, plan)

            await path_event_bus.publish(path_id, PathEvent(
                event_type="path.done", path_id=path_id, status="active",
                message="路径规划完成", progress=100, success=True,
            ))
        except Exception as exc:
            logger.error(f"路径规划任务异常: {exc}", exc_info=True)
            path = await self.session.get(LearningPath, path_id)
            if path:
                path.status = "failed"
                await self.session.commit()
            await path_event_bus.publish(path_id, PathEvent(
                event_type="path.done", path_id=path_id, status="failed",
                message=f"路径规划失败: {str(exc)}", progress=0, success=False,
            ))

    # ── 路径查询 ────────────────────────────────────────────────────────────

    async def get_active_path_overview(self, user_id: int, module: str = "mentor") -> LearningPathOverviewResponse | None:
        path = await self._get_active_path_record(user_id, module)
        if path is None:
            return None
        return await self._build_path_response(path)

    async def get_path_by_id(self, user_id: int, path_id: int) -> LearningPathOverviewResponse:
        path = await self._must_get_path(user_id, path_id)
        return await self._build_path_response(path)

    async def list_path_history(self, user_id: int, module: str = "mentor") -> list[LearningPathHistoryItem]:
        stmt = (
            select(LearningPath)
            .where(
                LearningPath.user_id == user_id,
                LearningPath.module == module,
            )
            .order_by(col(LearningPath.updated_at).desc())
        )
        paths = list((await self.session.exec(stmt)).all())
        return [
            LearningPathHistoryItem(
                id=path.id,
                title=path.title,
                goal=path.goal,
                topic=path.topic,
                overall_progress=path.overall_progress,
                status=path.status,
                current_node_key=path.current_node_key,
                updated_at=path.updated_at.isoformat() if path.updated_at else "",
            )
            for path in paths
        ]

    async def activate_history_path(self, user_id: int, path_id: int) -> LearningPathOverviewResponse:
        path = await self._must_get_path(user_id, path_id)
        await self._archive_active_paths(user_id, path.module, exclude_path_id=path.id)
        path.status = "active"
        path.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        return await self._build_path_response(path)

    # ── 节点工作区 ──────────────────────────────────────────────────────────

    async def get_node_workspace(self, user_id: int, node_id: int) -> LearningPathNodeWorkspaceResponse:
        """读取节点学习区状态，不触发任何 LLM 资源生成。"""
        node = await self._must_get_node(user_id, node_id)
        self._ensure_node_accessible(node)

        path = await self._must_get_path(user_id, node.path_id)
        tutorials = await self._get_node_tutorials(node.id)
        current = next((item for item in tutorials if item.is_current), None)
        resources = await self._get_node_resources(node.id)
        overview = await self._build_path_response(path)
        return LearningPathNodeWorkspaceResponse(
            path=overview,
            node=LearningPathNodeDTO.from_model(node),
            current_tutorial=LearningPathTutorialDTO.from_model(current) if current else None,
            tutorials=[LearningPathTutorialDTO.from_model(item) for item in tutorials],
            resources=[LearningPathResourceDTO.from_model(item) for item in resources],
            current_round=await self._get_latest_round(node.id),
            quiz_available=current is not None,
        )

    async def start_node_learning(self, user_id: int, node_id: int) -> LearningPathNodeWorkspaceResponse:
        """进入深入学习：标记节点开始，并懒加载生成主教程。"""
        node = await self._must_get_node(user_id, node_id)
        self._ensure_node_accessible(node)

        if node.status == "available":
            node.status = "in_progress"
            node.started_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(node)

        path = await self._must_get_path(user_id, node.path_id)
        tutorials = await self._get_node_tutorials(node.id)
        current = next((item for item in tutorials if item.is_current), None)
        if current is None:
            current = await self._create_tutorial(path=path, node=node, tutorial_type="primary")
            tutorials = await self._get_node_tutorials(node.id)

        resources = await self._get_node_resources(node.id)
        overview = await self._build_path_response(path)
        return LearningPathNodeWorkspaceResponse(
            path=overview,
            node=LearningPathNodeDTO.from_model(node),
            current_tutorial=LearningPathTutorialDTO.from_model(current),
            tutorials=[LearningPathTutorialDTO.from_model(item) for item in tutorials],
            resources=[LearningPathResourceDTO.from_model(item) for item in resources],
            current_round=await self._get_latest_round(node.id),
            quiz_available=current is not None,
        )

    async def generate_node_resource(
        self,
        user_id: int,
        node_id: int,
        payload: AuxiliaryResourceRequest,
    ) -> LearningPathResourceDTO:
        if payload.resource_type not in AUX_RESOURCE_TYPES:
            raise ValueError(f"不支持的资源类型: {payload.resource_type}")
        node = await self._must_get_node(user_id, node_id)
        self._ensure_node_accessible(node)
        self._ensure_node_in_deep_learning(node)
        path = await self._must_get_path(user_id, node.path_id)
        tutorial = await self._get_current_tutorial(node.id)
        if tutorial is None:
            tutorial = await self._create_tutorial(path=path, node=node, tutorial_type="primary")

        # Build structured NodeInput and call agent.generate_node()
        node_input = NodeInput(
            path_id=path.id,
            node_id=node.id,
            node_key=node.node_id,
            stage_id=node.stage_id,
            path_title=path.title,
            path_goal=path.goal,
            node_title=node.title,
            difficulty=node.difficulty,
            mastery_target=node.mastery_target,
            knowledge_points=list(tutorial.knowledge_points or []),
            weak_knowledge_points=list(tutorial.weak_knowledge_points or []),
            generation_focus=list(
                (node.resource_policy or {}).get("generation_focus", [])
            ),
            tutorial_title=tutorial.title,
            tutorial_summary=tutorial.summary,
            tutorial_markdown=tutorial.content_markdown,
            profile=await self._get_profile_dict(path.user_id),
            agent_config={},
        )

        agent = AGENT_REGISTRY[payload.resource_type]()
        result = await agent.generate_node(node_input)

        if not result.success:
            # Save failed record with error details
            current_count = await self._count_node_resources(node.id, payload.resource_type)
            resource = PathNodeResource(
                path_id=path.id,
                node_id=node.id,
                tutorial_id=tutorial.id,
                user_id=user_id,
                resource_type=payload.resource_type,
                version_no=current_count + 1,
                title=result.title or f"{node.title} - {payload.resource_type}",
                content_format=result.file_type or "markdown",
                status="failed",
                error_message=result.error,
                summary=result.summary,
                input_json=node_input.model_dump(mode="json"),
                metadata_json=result.metadata,
            )
            self.session.add(resource)
            await self.session.commit()
            await self.session.refresh(resource)
            return LearningPathResourceDTO.from_model(resource)

        # Save successful result
        current_count = await self._count_node_resources(node.id, payload.resource_type)
        content_json = None
        content_text = None
        if result.file_type == "json":
            try:
                content_json = json.loads(result.content) if isinstance(result.content, str) else result.content
            except json.JSONDecodeError:
                content_text = result.content
        else:
            content_text = result.content

        resource = PathNodeResource(
            path_id=path.id,
            node_id=node.id,
            tutorial_id=tutorial.id,
            user_id=user_id,
            resource_type=payload.resource_type,
            version_no=current_count + 1,
            title=result.title or f"{node.title} - {payload.resource_type}",
            content_format=result.file_type or "markdown",
            content_text=content_text,
            content_json=content_json,
            summary=result.summary,
            status="completed",
            input_json=node_input.model_dump(mode="json"),
            metadata_json=result.metadata,
        )
        self.session.add(resource)
        await self.session.commit()
        await self.session.refresh(resource)
        return LearningPathResourceDTO.from_model(resource)

    # ── 测验 ────────────────────────────────────────────────────────────────

    async def generate_node_questions(self, user_id: int, node_id: int) -> PathQuizRoundResponse:
        node = await self._must_get_node(user_id, node_id)
        self._ensure_node_accessible(node)
        self._ensure_node_in_deep_learning(node)
        path = await self._must_get_path(user_id, node.path_id)
        tutorial = await self._get_current_tutorial(node.id)
        if tutorial is None:
            tutorial = await self._create_tutorial(path=path, node=node, tutorial_type="primary")

        round_no = await self._get_latest_round(node.id) + 1
        generated = await self._generate_question_payload(path=path, node=node, tutorial=tutorial, round_no=round_no)
        if len(generated) != QUIZ_SIZE:
            raise ValueError("当前节点还没有生成完整的五道题，请稍后重试")
        questions: list[PathNodeQuestion] = []
        for index, item in enumerate(generated[:QUIZ_SIZE], start=1):
            question = PathNodeQuestion(
                path_id=path.id,
                node_id=node.id,
                tutorial_id=tutorial.id,
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
            self.session.add(question)
            questions.append(question)
        await self.session.commit()
        for question in questions:
            await self.session.refresh(question)
        return PathQuizRoundResponse(
            node_id=node.id,
            tutorial_id=tutorial.id,
            round_no=round_no,
            questions=[LearningPathQuestionDTO.from_model(item) for item in questions],
        )

    async def submit_node_quiz(
        self,
        user_id: int,
        node_id: int,
        payload: PathQuizSubmitRequest,
    ) -> PathQuizSubmitResponse:
        node = await self._must_get_node(user_id, node_id)
        path = await self._must_get_path(user_id, node.path_id)
        round_no = await self._get_latest_round(node.id)
        questions = await self._get_round_questions(node.id, round_no)
        if len(questions) != QUIZ_SIZE:
            raise ValueError("当前节点还没有完整的五道题")

        answer_map = {item.question_id: item.response for item in payload.answers}
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
        node.attempt_count += 1
        outcome = "passed"
        passed = score >= PASS_SCORE
        next_node_id: int | None = None

        if passed:
            node.status = "completed"
            node.completed_at = datetime.now(timezone.utc)
            await self._unlock_successors(path.id)
            next_node_id = await self._resolve_next_available_node_id(path.id)
            outcome = "passed"
        elif node.attempt_count == 1:
            await self._create_tutorial(
                path=path, node=node, tutorial_type="remediation",
                weak_knowledge_points=weak_points,
            )
            node.status = "remediation"
            outcome = "remediation"
            next_node_id = None
        elif node.attempt_count == 2:
            original = await self._get_primary_tutorial(node.id)
            await self._create_tutorial(
                path=path, node=node, tutorial_type="reinforced",
                weak_knowledge_points=weak_points,
                based_on_tutorial_id=original.id if original else None,
            )
            node.status = "completed_with_gaps"
            node.completed_at = datetime.now(timezone.utc)
            await self._unlock_successors(path.id)
            next_node_id = await self._resolve_next_available_node_id(path.id)
            outcome = "completed_with_gaps"
        else:
            node.status = "completed_with_gaps"
            node.completed_at = datetime.now(timezone.utc)
            await self._unlock_successors(path.id)
            next_node_id = await self._resolve_next_available_node_id(path.id)
            outcome = "completed_with_gaps"

        await self._update_path_progress(path)
        await self.session.commit()

        current_tutorial = await self._get_current_tutorial(node.id)
        await self._record_quiz_signal(
            user_id=user_id, path=path, node=node,
            score=score, weak_points=weak_points, outcome=outcome,
        )

        return PathQuizSubmitResponse(
            node_id=node.id,
            round_no=round_no,
            score=score,
            passed=passed,
            outcome=outcome,
            weak_knowledge_points=weak_points,
            next_node_id=next_node_id,
            current_tutorial_id=current_tutorial.id if current_tutorial else None,
        )

    # ── 评估 ────────────────────────────────────────────────────────────────

    async def get_learning_evaluation(self, user_id: int, path_id: int) -> PathLearningEvaluationResponse | None:
        path = await self._must_get_path(user_id, path_id)
        stmt = (
            select(LearningEvent)
            .where(LearningEvent.user_id == user_id, LearningEvent.path_id == path.id)
            .order_by(col(LearningEvent.created_at).desc())
            .limit(50)
        )
        events = list((await self.session.exec(stmt)).all())
        active_minutes = await self._get_path_active_minutes(user_id=user_id, path_id=path.id)
        summary = build_summary_from_events(events, active_minutes=active_minutes)
        signal_snapshot = LearningSignalSnapshot(
            average_score=summary.average_score,
            weak_topics=list(summary.weak_topics),
            preferred_resources=list(summary.preferred_resources),
            completed_resource_count=summary.completed_resources,
            viewed_resource_count=summary.viewed_resources,
            active_minutes=summary.active_minutes,
            recommendations=list(summary.recommendations),
        )
        current_node = await self._get_current_path_node(path.id, path.current_node_key)

        optimization_tips: list[str] = []
        average_score = signal_snapshot.average_score
        if average_score is not None and average_score < 70:
            optimization_tips.append("当前节点测验得分偏低，建议先围绕错题知识点做专项巩固。")
        if signal_snapshot.active_minutes < 10:
            optimization_tips.append("当前路径有效学习时长偏少，建议先完成当前节点教程后再继续测验。")
        if current_node is not None and current_node.attempt_count >= 2:
            optimization_tips.append("当前节点已多轮尝试，建议切换为强化教程并聚焦薄弱点复习。")
        if signal_snapshot.weak_topics:
            optimization_tips.append(f"优先巩固薄弱知识点：{signal_snapshot.weak_topics[0]}。")

        return PathLearningEvaluationResponse(
            path_id=path.id,
            overall_progress=path.overall_progress,
            current_node_key=path.current_node_key,
            signal_snapshot=signal_snapshot,
            needs_optimization=bool(optimization_tips),
            optimization_tips=optimization_tips,
        )

    async def record_learning_event(
        self,
        user_id: int,
        path_id: int,
        payload: LearningEventCreate,
    ) -> tuple[LearningEvent, dict[str, Any]]:
        path = await self._must_get_path(user_id, path_id)
        updates: dict[str, Any] = {"path_id": path.id}
        if payload.path_node_id is not None:
            node = await self._must_get_node(user_id, payload.path_node_id)
            if node.path_id != path.id:
                raise ValueError("学习事件节点不属于当前学习路径")
            updates["path_node_id"] = node.id
            updates["node_id"] = node.node_id
        payload = payload.model_copy(update=updates)
        event = await self.evaluation_service.record_event(
            self.session, user_id=user_id, payload=payload,
        )
        profile_payload = {
            "event_type": event.event_type,
            "session_id": event.session_id,
            "resource_id": event.resource_id,
            "resource_item_id": event.resource_item_id,
            "path_id": event.path_id,
            "path_node_id": event.path_node_id,
            "node_id": event.node_id,
            "course": event.course,
            "topic": event.topic,
            "score": event.score,
            "feedback": event.feedback,
            "metadata": event.metadata_json or {},
        }
        return event, profile_payload

    # ── 共享内部方法 ────────────────────────────────────────────────────────

    async def _must_get_path(self, user_id: int, path_id: int) -> LearningPath:
        path = await self.session.get(LearningPath, path_id)
        if path is None or path.user_id != user_id:
            raise ValueError("学习路径不存在")
        return path

    async def _must_get_node(self, user_id: int, node_id: int) -> PathNode:
        node = await self.session.get(PathNode, node_id)
        if node is None or node.user_id != user_id:
            raise ValueError("路径节点不存在")
        return node

    def _ensure_node_accessible(self, node: PathNode) -> None:
        if node.status not in ACCESSIBLE_NODE_STATUSES:
            raise ValueError("路径节点尚未解锁")

    def _ensure_node_in_deep_learning(self, node: PathNode) -> None:
        if node.status not in DEEP_LEARNING_NODE_STATUSES:
            raise ValueError("请先进入深入学习，再生成该节点的学习资源")

    async def _get_nodes_for_path(self, path_id: int) -> list[PathNode]:
        stmt = (
            select(PathNode)
            .where(PathNode.path_id == path_id)
            .order_by(col(PathNode.priority).asc(), col(PathNode.id).asc())
        )
        return list((await self.session.exec(stmt)).all())

    async def _get_node_tutorials(self, node_id: int) -> list[PathNodeTutorial]:
        stmt = (
            select(PathNodeTutorial)
            .where(PathNodeTutorial.node_id == node_id)
            .order_by(col(PathNodeTutorial.version_no).asc(), col(PathNodeTutorial.id).asc())
        )
        return list((await self.session.exec(stmt)).all())

    async def _get_node_resources(self, node_id: int) -> list[PathNodeResource]:
        stmt = (
            select(PathNodeResource)
            .where(PathNodeResource.node_id == node_id)
            .order_by(col(PathNodeResource.created_at).asc(), col(PathNodeResource.id).asc())
        )
        return list((await self.session.exec(stmt)).all())

    async def _get_current_tutorial(self, node_id: int) -> PathNodeTutorial | None:
        stmt = (
            select(PathNodeTutorial)
            .where(PathNodeTutorial.node_id == node_id, PathNodeTutorial.is_current.is_(True))
            .order_by(col(PathNodeTutorial.version_no).desc())
        )
        return (await self.session.exec(stmt)).first()

    async def _get_primary_tutorial(self, node_id: int) -> PathNodeTutorial | None:
        stmt = (
            select(PathNodeTutorial)
            .where(PathNodeTutorial.node_id == node_id, PathNodeTutorial.tutorial_type == "primary")
            .order_by(col(PathNodeTutorial.version_no).asc())
        )
        return (await self.session.exec(stmt)).first()

    async def _create_tutorial(
        self,
        *,
        path: LearningPath,
        node: PathNode,
        tutorial_type: str,
        weak_knowledge_points: list[str] | None = None,
        based_on_tutorial_id: int | None = None,
    ) -> PathNodeTutorial:
        payload = await self._generate_tutorial_payload(
            path=path, node=node, tutorial_type=tutorial_type,
            weak_knowledge_points=weak_knowledge_points or [],
        )
        current = await self._get_current_tutorial(node.id)
        if current is not None:
            current.is_current = False
        existing = await self._get_node_tutorials(node.id)
        tutorial = PathNodeTutorial(
            path_id=path.id,
            node_id=node.id,
            user_id=path.user_id,
            tutorial_type=tutorial_type,
            version_no=len(existing) + 1,
            based_on_tutorial_id=based_on_tutorial_id,
            is_current=True,
            title=payload["title"],
            summary=payload.get("summary"),
            content_markdown=payload["content_markdown"],
            knowledge_points=payload.get("knowledge_points") or [],
            weak_knowledge_points=weak_knowledge_points or [],
        )
        self.session.add(tutorial)
        await self.session.flush()
        node.current_tutorial_id = tutorial.id
        if node.started_at is None:
            node.started_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(tutorial)
        return tutorial

    async def _generate_tutorial_payload(
        self,
        *,
        path: LearningPath,
        node: PathNode,
        tutorial_type: str,
        weak_knowledge_points: list[str],
    ) -> dict[str, Any]:
        profile_md = await self.get_user_learning_profile(path.user_id)
        return await self.node_learning_agent.generate_tutorial(
            path_goal=path.goal,
            node_title=node.title,
            mastery_target=node.mastery_target or "掌握该节点核心能力",
            tutorial_type=tutorial_type,
            weak_knowledge_points=weak_knowledge_points,
            profile_markdown=profile_md,
        )

    async def _generate_question_payload(
        self, *, path: LearningPath, node: PathNode, tutorial: PathNodeTutorial, round_no: int,
    ) -> list[dict[str, Any]]:
        return await self.node_learning_agent.generate_questions(
            path_goal=path.goal,
            node_title=node.title,
            mastery_target=node.mastery_target or "掌握该节点核心能力",
            tutorial_title=tutorial.title,
            tutorial_summary=tutorial.summary or tutorial.title,
            round_no=round_no,
        )

    async def _get_latest_round(self, node_id: int) -> int:
        stmt = select(PathNodeQuestion).where(PathNodeQuestion.node_id == node_id)
        questions = list((await self.session.exec(stmt)).all())
        return max((item.round_no for item in questions), default=0)

    async def _get_round_questions(self, node_id: int, round_no: int) -> list[PathNodeQuestion]:
        stmt = (
            select(PathNodeQuestion)
            .where(PathNodeQuestion.node_id == node_id, PathNodeQuestion.round_no == round_no)
            .order_by(col(PathNodeQuestion.question_no).asc())
        )
        return list((await self.session.exec(stmt)).all())

    async def _unlock_successors(self, path_id: int) -> None:
        nodes = await self._get_nodes_for_path(path_id)
        completed = {item.node_id for item in nodes if item.status in COMPLETED_NODE_STATUSES}
        for node in nodes:
            if node.status == "locked" and set(node.prerequisites or []).issubset(completed):
                node.status = "available"
        if nodes:
            path = await self.session.get(LearningPath, path_id)
            next_node = next((item for item in nodes if item.status == "available"), None)
            if path is not None:
                path.current_node_key = next_node.node_id if next_node else path.current_node_key

    async def _resolve_next_available_node_id(self, path_id: int) -> int | None:
        nodes = await self._get_nodes_for_path(path_id)
        next_node = next((item for item in nodes if item.status == "available"), None)
        return next_node.id if next_node else None

    async def _update_path_progress(self, path: LearningPath) -> None:
        nodes = await self._get_nodes_for_path(path.id)
        if not nodes:
            path.overall_progress = 0
            return
        completed = sum(1 for item in nodes if item.status in COMPLETED_NODE_STATUSES)
        path.overall_progress = round(completed / len(nodes) * 100)
        next_node = next((item for item in nodes if item.status in ACTIVE_NODE_STATUSES), None)
        path.current_node_key = next_node.node_id if next_node else None
        if completed == len(nodes):
            path.status = "completed"
        path.updated_at = datetime.now(timezone.utc)

    async def _record_quiz_signal(
        self, *, user_id: int, path: LearningPath, node: PathNode,
        score: int, weak_points: list[str], outcome: str,
    ) -> None:
        payload = LearningEventCreate(
            event_type="quiz_submitted",
            path_id=path.id,
            path_node_id=node.id,
            node_id=node.node_id,
            course=path.title,
            topic=node.title,
            score=float(score / QUIZ_SIZE * 100),
            feedback=None,
            metadata={"weak_knowledge_points": weak_points, "outcome": outcome},
        )
        event = await self.evaluation_service.record_event(self.session, user_id=user_id, payload=payload)
        await bg_apply_profile_update_from_learning_event(
            user_id,
            {
                "event_type": event.event_type,
                "session_id": event.session_id,
                "resource_id": event.resource_id,
                "resource_item_id": event.resource_item_id,
                "path_id": event.path_id,
                "path_node_id": event.path_node_id,
                "node_id": event.node_id,
                "course": event.course,
                "topic": event.topic,
                "score": event.score,
                "feedback": event.feedback,
                "metadata": event.metadata_json or {},
            },
        )

    async def _count_node_resources(self, node_id: int, resource_type: str) -> int:
        stmt = select(PathNodeResource).where(
            PathNodeResource.node_id == node_id,
            PathNodeResource.resource_type == resource_type,
        )
        return len(list((await self.session.exec(stmt)).all()))

    async def _get_profile_dict(self, user_id: int) -> dict[str, Any]:
        try:
            profile = await self.profile_builder.get_or_create_global_profile(user_id=user_id)
            return profile.profile_json if profile and profile.profile_json else {}
        except ProgrammingError as exc:
            logger.warning("[PathService] 画像表暂不可用，路径规划降级为空画像: user_id=%s error=%s", user_id, exc)
            return {}

    async def get_user_learning_profile(self, user_id: int) -> str:
        try:
            return await self.profile_builder.get_profile_markdown(user_id)
        except ProgrammingError as exc:
            logger.warning("[PathService] 画像文本暂不可用，教程生成降级无画像: user_id=%s error=%s", user_id, exc)
            return ""

    async def _archive_active_paths(self, user_id: int, module: str, exclude_path_id: int | None = None) -> None:
        stmt = select(LearningPath).where(
            LearningPath.user_id == user_id,
            LearningPath.module == module,
            LearningPath.status == "active",
        )
        paths = list((await self.session.exec(stmt)).all())
        for item in paths:
            if exclude_path_id is not None and item.id == exclude_path_id:
                continue
            item.status = "archived"
            item.updated_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def _get_active_path_record(self, user_id: int, module: str = "mentor") -> LearningPath | None:
        stmt = (
            select(LearningPath)
            .where(
                LearningPath.user_id == user_id,
                LearningPath.module == module,
                LearningPath.status == "active",
            )
            .order_by(col(LearningPath.updated_at).desc())
        )
        return (await self.session.exec(stmt)).first()

    async def _build_path_response(self, path: LearningPath) -> LearningPathOverviewResponse:
        nodes = await self._get_nodes_for_path(path.id)
        return LearningPathOverviewResponse(
            id=path.id,
            module=path.module,
            title=path.title,
            goal=path.goal,
            topic=path.topic,
            overall_progress=path.overall_progress,
            eta_days=path.eta_days,
            confidence=path.confidence,
            status=path.status,
            current_node_key=path.current_node_key,
            stages=list(path.stages_json or []),
            nodes=[LearningPathNodeDTO.from_model(item) for item in nodes],
            created_at=path.created_at.isoformat() if path.created_at else "",
            updated_at=path.updated_at.isoformat() if path.updated_at else "",
        )

    async def _get_path_active_minutes(self, *, user_id: int, path_id: int) -> int:
        stmt = select(LearningSession).where(
            LearningSession.user_id == user_id,
            LearningSession.path_id == path_id,
        )
        sessions = list((await self.session.exec(stmt)).all())
        return sum(item.duration_seconds or 0 for item in sessions) // 60

    async def _get_current_path_node(self, path_id: int, current_node_key: str | None) -> PathNode | None:
        if not current_node_key:
            return None
        stmt = select(PathNode).where(
            PathNode.path_id == path_id,
            PathNode.node_id == current_node_key,
        )
        return (await self.session.exec(stmt)).first()

    def _stage_to_dict(self, stage: Any) -> dict[str, Any]:
        if hasattr(stage, "model_dump"):
            return stage.model_dump(mode="json")
        return dict(stage)


# ── 模块级辅助函数 ─────────────────────────────────────────────────────────


def build_learning_event_item(event: LearningEvent) -> LearningEventItem:
    return LearningEventItem(
        id=event.id or 0,
        event_type=event.event_type,
        resource_id=event.resource_id,
        resource_item_id=event.resource_item_id,
        path_id=event.path_id,
        path_node_id=event.path_node_id,
        node_id=event.node_id,
        course=event.course,
        topic=event.topic,
        score=event.score,
        feedback=event.feedback,
        created_at=event.created_at,
    )


async def run_generation_bg(user_id: int, path_id: int, request: CreateLearningPathRequest):
    from app.infra.database import session_scope

    async with session_scope() as session:
        service = PathService(session)
        await service.run_generation(path_id, user_id, request)
