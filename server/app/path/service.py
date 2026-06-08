from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.evaluation.request import LearningEventCreate
from app.evaluation.service import EvaluationService, build_summary_from_events
from app.infra.llm import get_llm
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
from app.memory.service import MemoryService
from app.path.agents.planner import PathPlannerAgent
from app.path.agents.planner import repair_generated_plan_from_macro_stages
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
from app.resource.agents import AGENT_REGISTRY
from app.resource.schemas import WorkerState

logger = get_logger(__name__)

PASS_SCORE = 3
QUIZ_SIZE = 5
AUX_RESOURCE_TYPES = {"mindmap", "code", "ppt"}


class LearningPathService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.memory_service = MemoryService(module="mentor")
        self.evaluation_service = EvaluationService()
        self.path_planner = PathPlannerAgent()
        self.llm = get_llm()

    async def create_path(self, user_id: int, request: CreateLearningPathRequest) -> LearningPathOverviewResponse:
        await self._archive_active_paths(user_id, request.module)
        profile = await self._get_profile_dict(user_id)
        plan = await self._generate_path_plan(user_id=user_id, request=request, profile=profile)
        plan = repair_generated_plan_from_macro_stages(
            plan=plan,
            macro_stages=list(getattr(plan, "stages", []) or []),
            request=request,
            strategy_report=getattr(plan, "strategy_report", ""),
        )

        path = LearningPath(
            user_id=user_id,
            module=request.module,
            title=plan.title,
            goal=request.goal,
            topic=request.topic or None,
            overall_progress=0,
            eta_days=plan.eta_days,
            confidence=plan.confidence,
            status="active",
            stages_json=[self._stage_to_dict(stage) for stage in plan.stages],
            strategy_report=getattr(plan, "strategy_report", None),
            adjustment_rationale=list(getattr(plan, "adjustment_rationale", []) or []),
        )
        self.session.add(path)
        await self.session.flush()

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
        await self.session.refresh(path)
        for node in nodes:
            await self.session.refresh(node)
        return self._build_path_overview(path, nodes)

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

    async def get_node_workspace(self, user_id: int, node_id: int) -> LearningPathNodeWorkspaceResponse:
        node = await self._must_get_node(user_id, node_id)
        path = await self._must_get_path(user_id, node.path_id)
        tutorials = await self._get_node_tutorials(node.id)
        current = next((item for item in tutorials if item.is_current), None)
        if current is None:
            current = await self._create_tutorial(path=path, node=node, tutorial_type="primary")
            tutorials = await self._get_node_tutorials(node.id)
        resources = await self._get_node_resources(node.id)
        current_round = await self._get_latest_round(node.id)
        overview = await self._build_path_response(path)
        return LearningPathNodeWorkspaceResponse(
            path=overview,
            node=self._to_node_dto(node),
            current_tutorial=self._to_tutorial_dto(current),
            tutorials=[self._to_tutorial_dto(item) for item in tutorials],
            resources=[self._to_resource_dto(item) for item in resources],
            current_round=current_round,
            quiz_available=current is not None,
        )

    async def generate_node_questions(self, user_id: int, node_id: int) -> PathQuizRoundResponse:
        node = await self._must_get_node(user_id, node_id)
        path = await self._must_get_path(user_id, node.path_id)
        tutorial = await self._get_current_tutorial(node.id)
        if tutorial is None:
            tutorial = await self._create_tutorial(path=path, node=node, tutorial_type="primary")

        round_no = await self._get_latest_round(node.id) + 1
        generated = await self._generate_question_payload(path=path, node=node, tutorial=tutorial, round_no=round_no)
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
            questions=[self._to_question_dto(item) for item in questions],
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
            tutorial = await self._create_tutorial(
                path=path,
                node=node,
                tutorial_type="remediation",
                weak_knowledge_points=weak_points,
            )
            outcome = "remediation"
            next_node_id = None
        elif node.attempt_count == 2:
            original = await self._get_primary_tutorial(node.id)
            tutorial = await self._create_tutorial(
                path=path,
                node=node,
                tutorial_type="reinforced",
                weak_knowledge_points=weak_points,
                based_on_tutorial_id=original.id if original else None,
            )
            outcome = "reinforced"
            next_node_id = None
        else:
            node.status = "completed_with_gaps"
            node.completed_at = datetime.now(timezone.utc)
            await self._unlock_successors(path.id)
            next_node_id = await self._resolve_next_available_node_id(path.id)
            tutorial = await self._get_current_tutorial(node.id)
            outcome = "completed_with_gaps"

        await self._update_path_progress(path)
        await self.session.commit()

        current_tutorial = await self._get_current_tutorial(node.id)
        await self._record_quiz_signal(
            user_id=user_id,
            path=path,
            node=node,
            score=score,
            weak_points=weak_points,
            outcome=outcome,
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

    async def generate_node_resource(
        self,
        user_id: int,
        node_id: int,
        payload: AuxiliaryResourceRequest,
    ) -> LearningPathResourceDTO:
        if payload.resource_type not in AUX_RESOURCE_TYPES:
            raise ValueError("仅支持 mindmap、code、ppt")
        node = await self._must_get_node(user_id, node_id)
        path = await self._must_get_path(user_id, node.path_id)
        tutorial = await self._get_current_tutorial(node.id)
        if tutorial is None:
            tutorial = await self._create_tutorial(path=path, node=node, tutorial_type="primary")
        generated = await self._generate_auxiliary_resource_payload(
            path=path,
            node=node,
            tutorial=tutorial,
            resource_type=payload.resource_type,
        )
        current_count = await self._count_node_resources(node.id, payload.resource_type)
        resource = PathNodeResource(
            path_id=path.id,
            node_id=node.id,
            tutorial_id=tutorial.id,
            user_id=user_id,
            resource_type=payload.resource_type,
            version_no=current_count + 1,
            title=generated["title"],
            content_format=generated["content_format"],
            content_text=generated.get("content_text"),
            content_json=generated.get("content_json"),
            metadata_json=generated.get("metadata") or {},
        )
        self.session.add(resource)
        await self.session.commit()
        await self.session.refresh(resource)
        return self._to_resource_dto(resource)

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
    ) -> LearningEvent:
        return await self.evaluation_service.record_event(
            self.session,
            user_id=user_id,
            payload=payload,
        )

    async def list_path_resources(self, user_id: int, limit: int, offset: int) -> dict[str, Any]:
        stmt = (
            select(PathNodeResource)
            .where(PathNodeResource.user_id == user_id)
            .order_by(col(PathNodeResource.created_at).desc())
            .offset(offset)
            .limit(limit)
        )
        rows = list((await self.session.exec(stmt)).all())
        node_map: dict[int, PathNode] = {}
        if rows:
            node_ids = {row.node_id for row in rows}
            node_rows = list((await self.session.exec(select(PathNode).where(PathNode.id.in_(node_ids)))).all())
            node_map = {node.id: node for node in node_rows if node.id is not None}
        total_stmt = select(PathNodeResource).where(PathNodeResource.user_id == user_id)
        total = len(list((await self.session.exec(total_stmt)).all()))
        return {
            "items": [
                {
                    "id": row.id,
                    "learning_need": row.title,
                    "status": "completed",
                    "resource_types": [row.resource_type],
                    "resource_type": row.resource_type,
                    "title": row.title,
                    "path_id": row.path_id,
                    "path_node_id": row.node_id,
                    "node_id": node_map.get(row.node_id).node_id if node_map.get(row.node_id) else None,
                    "node_title": node_map.get(row.node_id).title if node_map.get(row.node_id) else None,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                }
                for row in rows
            ],
            "total": total,
        }

    async def get_path_resource_bundle(self, user_id: int, resource_id: int) -> LearningPathResourceDTO | None:
        resource = await self.session.get(PathNodeResource, resource_id)
        if resource is None or resource.user_id != user_id:
            return None
        return self._to_resource_dto(resource)

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

    async def _build_path_response(self, path: LearningPath) -> LearningPathOverviewResponse:
        nodes = await self._get_nodes_for_path(path.id)
        return self._build_path_overview(path, nodes)

    def _build_path_overview(self, path: LearningPath, nodes: Sequence[PathNode]) -> LearningPathOverviewResponse:
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
            strategy_report=path.strategy_report,
            adjustment_rationale=list(path.adjustment_rationale or []),
            stages=list(path.stages_json or []),
            nodes=[self._to_node_dto(item) for item in nodes],
            created_at=path.created_at.isoformat() if path.created_at else "",
            updated_at=path.updated_at.isoformat() if path.updated_at else "",
        )

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
            path=path,
            node=node,
            tutorial_type=tutorial_type,
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
        completed = {item.node_id for item in nodes if item.status in {"completed", "completed_with_gaps"}}
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
        completed = sum(1 for item in nodes if item.status in {"completed", "completed_with_gaps"})
        path.overall_progress = round(completed / len(nodes) * 100)
        next_node = next((item for item in nodes if item.status == "available"), None)
        path.current_node_key = next_node.node_id if next_node else None
        if completed == len(nodes):
            path.status = "completed"
        path.updated_at = datetime.now(timezone.utc)

    async def _count_node_resources(self, node_id: int, resource_type: str) -> int:
        stmt = select(PathNodeResource).where(
            PathNodeResource.node_id == node_id,
            PathNodeResource.resource_type == resource_type,
        )
        return len(list((await self.session.exec(stmt)).all()))

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

    async def _record_quiz_signal(
        self,
        *,
        user_id: int,
        path: LearningPath,
        node: PathNode,
        score: int,
        weak_points: list[str],
        outcome: str,
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
            metadata={
                "weak_knowledge_points": weak_points,
                "outcome": outcome,
            },
        )
        await self.evaluation_service.record_event(self.session, user_id=user_id, payload=payload)

    async def _get_profile_dict(self, user_id: int) -> dict[str, Any]:
        profile = await self.memory_service.get_or_create_profile(user_id=user_id)
        return profile.profile_json if profile and profile.profile_json else {}

    async def _generate_path_plan(
        self,
        *,
        user_id: int,
        request: CreateLearningPathRequest,
        profile: dict[str, Any],
    ) -> AgentLearningPathPlan:
        plan, _search = await self.path_planner.generate_plan(
            request,
            profile,
        )
        return plan

    async def _generate_tutorial_payload(
        self,
        *,
        path: LearningPath,
        node: PathNode,
        tutorial_type: str,
        weak_knowledge_points: list[str],
    ) -> dict[str, Any]:
        prompt = self._build_tutorial_prompt(path, node, tutorial_type, weak_knowledge_points)
        response = await self.llm.ainvoke(prompt, temperature=0.3)
        content = response.content if hasattr(response, "content") else str(response)
        return {
            "title": f"{node.title} - {tutorial_type}",
            "summary": tutorial_type,
            "content_markdown": content,
            "knowledge_points": [node.title],
        }

    async def _generate_question_payload(
        self,
        *,
        path: LearningPath,
        node: PathNode,
        tutorial: PathNodeTutorial,
        round_no: int,
    ) -> list[dict[str, Any]]:
        state = WorkerState(
            learning_need=f"{path.goal}\n当前节点：{node.title}\n教程摘要：{tutorial.summary or tutorial.title}",
            profile=await self._get_profile_dict(path.user_id),
            agent_config={
                "question_count": QUIZ_SIZE,
                "difficulty_mode": "basic",
                "include_analysis": True,
                "question_types": ["single"],
            },
        )
        result = await AGENT_REGISTRY["quiz"]().run(state)
        payload = json.loads(result.content)
        questions = payload.get("questions") or []
        normalized: list[dict[str, Any]] = []
        for item in questions[:QUIZ_SIZE]:
            options = item.get("options") or []
            choice = {}
            for option in options:
                if isinstance(option, dict):
                    choice[str(option.get("label"))] = option.get("content")
            normalized.append(
                {
                    "question": item.get("question", ""),
                    "choice": choice,
                    "answer": item.get("answer", ""),
                    "analysis": item.get("explanation", ""),
                    "knowledge_points": item.get("knowledge_points") or [node.title],
                    "type": "single_choice",
                }
            )
        return normalized

    async def _generate_auxiliary_resource_payload(
        self,
        *,
        path: LearningPath,
        node: PathNode,
        tutorial: PathNodeTutorial,
        resource_type: str,
    ) -> dict[str, Any]:
        state = WorkerState(
            learning_need=f"{path.goal}\n当前节点：{node.title}\n教程内容：{tutorial.content_markdown[:1200]}",
            profile=await self._get_profile_dict(path.user_id),
            agent_config={},
        )
        result = await AGENT_REGISTRY[resource_type]().run(state)
        if result.file_type == "json":
            return {
                "title": result.title or f"{node.title} - {resource_type}",
                "content_format": "json",
                "content_text": None,
                "content_json": json.loads(result.content),
                "metadata": result.metadata,
            }
        return {
            "title": result.title or f"{node.title} - {resource_type}",
            "content_format": result.file_type or "markdown",
            "content_text": result.content,
            "content_json": None,
            "metadata": result.metadata,
        }

    def _build_tutorial_prompt(
        self,
        path: LearningPath,
        node: PathNode,
        tutorial_type: str,
        weak_knowledge_points: list[str],
    ) -> str:
        prompt_parts = [
            f"学习目标：{path.goal}",
            f"当前节点：{node.title}",
            f"掌握目标：{node.mastery_target or '掌握该节点核心能力'}",
            f"教程类型：{tutorial_type}",
        ]
        if weak_knowledge_points:
            prompt_parts.append(f"重点围绕这些薄弱知识点强化：{', '.join(weak_knowledge_points)}")
        prompt_parts.append("请输出一份中文 Markdown 教程，结构清晰，直接用于学习。")
        return "\n".join(prompt_parts)

    def _stage_to_dict(self, stage: Any) -> dict[str, Any]:
        if hasattr(stage, "model_dump"):
            return stage.model_dump(mode="json")
        if isinstance(stage, dict):
            return stage
        return {
            "stage_id": getattr(stage, "stage_id", ""),
            "title": getattr(stage, "title", ""),
            "description": getattr(stage, "description", ""),
        }

    def _to_node_dto(self, node: PathNode) -> LearningPathNodeDTO:
        return LearningPathNodeDTO(
            id=node.id,
            node_id=node.node_id,
            stage_id=node.stage_id,
            title=node.title,
            status=node.status,
            priority=node.priority,
            attempt_count=node.attempt_count,
            mastery_target=node.mastery_target,
            estimated_minutes=node.estimated_minutes,
            difficulty=node.difficulty,
            recommendation_reason=node.recommendation_reason,
            prerequisites=list(node.prerequisites or []),
            current_tutorial_id=node.current_tutorial_id,
        )

    def _to_tutorial_dto(self, tutorial: PathNodeTutorial) -> LearningPathTutorialDTO:
        return LearningPathTutorialDTO(
            id=tutorial.id,
            tutorial_type=tutorial.tutorial_type,
            version_no=tutorial.version_no,
            based_on_tutorial_id=tutorial.based_on_tutorial_id,
            title=tutorial.title,
            summary=tutorial.summary,
            content_markdown=tutorial.content_markdown,
            knowledge_points=list(tutorial.knowledge_points or []),
            weak_knowledge_points=list(tutorial.weak_knowledge_points or []),
            created_at=tutorial.created_at.isoformat() if tutorial.created_at else "",
        )

    def _to_question_dto(self, question: PathNodeQuestion) -> LearningPathQuestionDTO:
        return LearningPathQuestionDTO(
            id=question.id,
            question_no=question.question_no,
            round_no=question.round_no,
            mode=question.mode,
            type=question.type,
            question=question.question,
            choice=dict(question.choice or {}),
            answer=question.answer,
            response=question.response,
            analysis=question.analysis,
            knowledge_points=list(question.knowledge_points or []),
            is_correct=question.is_correct,
        )

    def _to_resource_dto(self, resource: PathNodeResource) -> LearningPathResourceDTO:
        return LearningPathResourceDTO(
            id=resource.id,
            resource_type=resource.resource_type,
            version_no=resource.version_no,
            title=resource.title,
            content_format=resource.content_format,
            content_text=resource.content_text,
            content_json=resource.content_json,
            metadata=dict(resource.metadata_json or {}),
            created_at=resource.created_at.isoformat() if resource.created_at else "",
        )
