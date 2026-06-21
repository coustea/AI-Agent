from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import ProgrammingError
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import PATH_QUIZ_SIZE
from app.evaluation.request import LearningEventCreate
from app.evaluation.response import LearningEventItem
from app.evaluation.service import (
    EvaluationService,
    build_summary_from_events,
)
from app.infra.database import session_scope
from app.infra.agent_events import AgentEventEmitter
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
    LearnState,
    validate_path_plan,
)
from app.path.workflows import (
    PathPlannerAgent,
    get_learn_workflow,
    ACTIVE_NODE_STATUSES,
    COMPLETED_NODE_STATUSES,
)
from app.profile.service import get_profile_service


logger = get_logger(__name__)

AUX_RESOURCE_TYPES = {"content", "mindmap", "code", "reading", "quiz", "ppt"}
STARTED_NODE_STATUSES = {"in_progress", "remediation", "reinforced"}
ACCESSIBLE_NODE_STATUSES = ACTIVE_NODE_STATUSES | COMPLETED_NODE_STATUSES
DEEP_LEARNING_NODE_STATUSES = STARTED_NODE_STATUSES | COMPLETED_NODE_STATUSES


class PathService:

    def __init__(self, session: AsyncSession):
        self.session = session
        self.profile_builder = get_profile_service()
        self.path_planner = PathPlannerAgent()
        self.evaluation_service = EvaluationService()
        self.learn_graph = get_learn_workflow()

    # ── 路径规划 ────────────────────────────────────────────────────────────

    async def init_path_task(
        self, user_id: int, request: CreateLearningPathRequest
    ) -> int:
        await self._archive_active_paths(user_id, request.module)
        path = LearningPath(
            user_id=user_id,
            module=request.module,
            title=request.topic or "学习路径",
            goal=request.goal,
            topic=request.topic or None,
            overall_progress=0,
            status="generating",
            stages_json=[],
        )
        self.session.add(path)
        await self.session.commit()
        await self.session.refresh(path)
        return path.id

    async def _persist_path_plan(
        self, path_id: int, user_id: int, plan: AgentLearningPathPlan
    ) -> None:
        path = await self.session.get(LearningPath, path_id)
        if not path:
            return
        validate_path_plan(plan)

        path.status = "active"
        path.title = plan.title
        path.stages_json = [
            self._stage_to_dict(stage) for stage in plan.stages
        ]

        completed_keys: set[str] = set()
        nodes: list[PathNode] = []
        for index, node_data in enumerate(plan.nodes):
            prerequisites = list(
                getattr(node_data, "prerequisites", []) or []
            )
            status = (
                "available"
                if not prerequisites
                or set(prerequisites).issubset(completed_keys)
                else "locked"
            )
            node = PathNode(
                path_id=path.id,
                user_id=user_id,
                node_id=node_data.node_id,
                stage_id=node_data.stage_id,
                title=node_data.title,
                status=status,
                priority=index + 1,
                prerequisites=prerequisites,
                difficulty=getattr(node_data, "difficulty", None),
            )
            self.session.add(node)
            nodes.append(node)
        if nodes:
            path.current_node_key = nodes[0].node_id
        await self.session.commit()

    async def run_generation(
        self,
        path_id: int,
        user_id: int,
        request: CreateLearningPathRequest,
        run_id: str,
    ) -> None:
        emitter = AgentEventEmitter(run_id=run_id, module="path", business_id=str(path_id))

        async def progress_cb(status: str, progress: int, message: str):
            await emitter.agent_status(
                activity_id=f"path-plan:{path_id}",
                agent_id="path_planner",
                title=message,
                summary=message,
                progress=progress,
            )

        try:
            await emitter.started(title="路径规划已开始")
            profile = await self._get_profile_dict(user_id)
            profile_md = await self.get_user_learning_profile(user_id)
            await emitter.agent_status(
                activity_id=f"path-plan:{path_id}",
                agent_id="path_planner",
                title="正在初始化路径推演引擎",
                summary="正在初始化路径推演引擎",
                progress=10,
            )

            plan = await self.path_planner.generate_plan(
                request,
                profile,
                progress_callback=progress_cb,
                profile_markdown=profile_md,
            )

            await emitter.agent_status(
                activity_id=f"path-plan:{path_id}",
                agent_id="path_planner",
                title="正在生成节点结构",
                summary="正在生成节点结构",
                progress=85,
            )

            plan = repair_generated_plan_from_macro_stages(
                plan=plan,
                macro_stages=list(getattr(plan, "stages", []) or []),
                request=request,
            )

            validate_path_plan(plan)
            await self._persist_path_plan(path_id, user_id, plan)

            await emitter.completed(title="路径规划完成", progress=100)
        except Exception as exc:
            logger.error(f"路径规划任务异常: {exc}", exc_info=True)
            path = await self.session.get(LearningPath, path_id)
            if path:
                path.status = "failed"
                await self.session.commit()
            await emitter.failed(
                title="路径规划失败",
                summary="暂时无法完成本次路径规划",
                progress=0,
            )

    # ── 路径查询 ────────────────────────────────────────────────────────────

    async def get_active_path_overview(
        self, user_id: int, module: str = "mentor"
    ) -> LearningPathOverviewResponse | None:
        path = await self._get_active_path_record(user_id, module)
        if path is None:
            return None
        return await self._build_path_response(path)

    async def get_path_by_id(
        self, user_id: int, path_id: int
    ) -> LearningPathOverviewResponse:
        path = await self._must_get_path(user_id, path_id)
        return await self._build_path_response(path)

    async def list_path_history(
        self, user_id: int, module: str = "mentor"
    ) -> list[LearningPathHistoryItem]:
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
                updated_at=(
                    path.updated_at.isoformat() if path.updated_at else ""
                ),
            )
            for path in paths
        ]

    async def activate_history_path(
        self, user_id: int, path_id: int
    ) -> LearningPathOverviewResponse:
        path = await self._must_get_path(user_id, path_id)
        await self._archive_active_paths(
            user_id, path.module, exclude_path_id=path.id
        )
        path.status = "active"
        path.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        return await self._build_path_response(path)

    # ── 节点工作区 ──────────────────────────────────────────────────────────

    async def get_node_workspace(
        self, user_id: int, node_id: int
    ) -> LearningPathNodeWorkspaceResponse:
        node = await self._must_get_node(user_id, node_id)
        self._ensure_node_accessible(node)
        return await self._build_workspace_response(node)

    async def start_node_learning(
        self, user_id: int, node_id: int
    ) -> LearningPathNodeWorkspaceResponse:
        node = await self._must_get_node(user_id, node_id)
        self._ensure_node_accessible(node)

        tutorials = await self._get_node_tutorials(node.id)
        current = next((t for t in tutorials if t.is_current), None)

        if current is None:
            state = LearnState(
                user_id=user_id,
                node_id=node_id,
                phase="start",
                session=self.session,
                tutorial_type="primary",
            )
            result = await self.learn_graph.ainvoke(state)
            if result.get("error"):
                raise ValueError(result["error"])
        elif node.status == "available":
            node.status = "in_progress"
            node.started_at = datetime.now(timezone.utc)
            await self.session.commit()

        node = await self._must_get_node(user_id, node_id)
        return await self._build_workspace_response(node)

    async def _build_workspace_response(
        self, node: PathNode
    ) -> LearningPathNodeWorkspaceResponse:
        path = await self._must_get_path(node.user_id, node.path_id)
        tutorials = await self._get_node_tutorials(node.id)
        current = next((t for t in tutorials if t.is_current), None)
        resources = await self._get_node_resources(node.id)
        overview = await self._build_path_response(path)
        return LearningPathNodeWorkspaceResponse(
            path=overview,
            node=LearningPathNodeDTO.from_model(node),
            current_tutorial=(
                LearningPathTutorialDTO.from_model(current)
                if current
                else None
            ),
            tutorials=[
                LearningPathTutorialDTO.from_model(t) for t in tutorials
            ],
            resources=[
                LearningPathResourceDTO.from_model(r) for r in resources
            ],
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

        state = LearnState(
            user_id=user_id,
            node_id=node_id,
            phase="resource",
            session=self.session,
            resource_type=payload.resource_type,
        )
        result = await self.learn_graph.ainvoke(state)
        if result.get("error"):
            raise ValueError(result["error"])

        resource_dto = result.get("resource_dto", {})
        return LearningPathResourceDTO(**resource_dto)

    # ── 测验 ────────────────────────────────────────────────────────────────

    async def generate_node_questions(
        self, user_id: int, node_id: int
    ) -> PathQuizRoundResponse:
        node = await self._must_get_node(user_id, node_id)
        self._ensure_node_accessible(node)
        self._ensure_node_in_deep_learning(node)

        state = LearnState(
            user_id=user_id,
            node_id=node_id,
            phase="questions",
            session=self.session,
        )
        result = await self.learn_graph.ainvoke(state)
        if result.get("error"):
            raise ValueError(result["error"])

        questions = result.get("quiz_questions", [])
        current_tutorial = result.get("current_tutorial")
        round_no = result.get("round_no", 1)
        return PathQuizRoundResponse(
            node_id=node.id,
            tutorial_id=current_tutorial.id if current_tutorial else None,
            round_no=round_no,
            questions=[LearningPathQuestionDTO.from_model(q) for q in questions],
        )

    async def submit_node_quiz(
        self,
        user_id: int,
        node_id: int,
        payload: PathQuizSubmitRequest,
    ) -> PathQuizSubmitResponse:
        node = await self._must_get_node(user_id, node_id)
        self._ensure_node_accessible(node)
        self._ensure_node_in_deep_learning(node)

        round_no = await self._get_latest_round(node.id)
        questions = await self._get_round_questions(node.id, round_no)
        if len(questions) != PATH_QUIZ_SIZE:
            raise ValueError("当前节点还没有完整的五道题")

        state = LearnState(
            user_id=user_id,
            node_id=node_id,
            phase="quiz",
            session=self.session,
            quiz_answers=[
                {"question_id": a.question_id, "response": a.response}
                for a in payload.answers
            ],
            quiz_questions=questions,
            round_no=round_no,
        )
        result = await self.learn_graph.ainvoke(state)
        if result.get("error"):
            raise ValueError(result["error"])

        current_tutorial = await self._get_current_tutorial(node.id)
        return PathQuizSubmitResponse(
            node_id=node.id,
            round_no=round_no,
            score=result["score"],
            passed=result["passed"],
            outcome=result["outcome"],
            weak_knowledge_points=result.get("weak_knowledge_points", []),
            next_node_id=result.get("next_node_id"),
            current_tutorial_id=(
                current_tutorial.id if current_tutorial else None
            ),
        )

    # ── 评估 ────────────────────────────────────────────────────────────────

    async def get_learning_evaluation(
        self, user_id: int, path_id: int
    ) -> PathLearningEvaluationResponse | None:
        path = await self._must_get_path(user_id, path_id)
        stmt = (
            select(LearningEvent)
            .where(
                LearningEvent.user_id == user_id,
                LearningEvent.path_id == path.id,
            )
            .order_by(col(LearningEvent.created_at).desc())
            .limit(50)
        )
        events = list((await self.session.exec(stmt)).all())
        active_minutes = await self._get_path_active_minutes(
            user_id=user_id, path_id=path.id
        )
        summary = build_summary_from_events(
            events, active_minutes=active_minutes
        )
        signal_snapshot = LearningSignalSnapshot(
            average_score=summary.average_score,
            weak_topics=list(summary.weak_topics),
            preferred_resources=list(summary.preferred_resources),
            completed_resource_count=summary.completed_resources,
            viewed_resource_count=summary.viewed_resources,
            active_minutes=summary.active_minutes,
            recommendations=list(summary.recommendations),
        )
        current_node = await self._get_current_path_node(
            path.id, path.current_node_key
        )

        optimization_tips: list[str] = []
        average_score = signal_snapshot.average_score
        if average_score is not None and average_score < 70:
            optimization_tips.append(
                "当前节点测验得分偏低，建议先围绕错题知识点做专项巩固。"
            )
        if signal_snapshot.active_minutes < 10:
            optimization_tips.append(
                "当前路径有效学习时长偏少，建议先完成当前节点教程后再继续测验。"
            )
        if current_node is not None and current_node.attempt_count >= 2:
            optimization_tips.append(
                "当前节点已多轮尝试，建议切换为强化教程并聚焦薄弱点复习。"
            )
        if signal_snapshot.weak_topics:
            optimization_tips.append(
                f"优先巩固薄弱知识点：{signal_snapshot.weak_topics[0]}。"
            )

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
            self.session,
            user_id=user_id,
            payload=payload,
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

    async def _must_get_path(
        self, user_id: int, path_id: int
    ) -> LearningPath:
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

    async def _get_nodes_for_path(
        self, path_id: int
    ) -> list[PathNode]:
        stmt = (
            select(PathNode)
            .where(PathNode.path_id == path_id)
            .order_by(
                col(PathNode.priority).asc(), col(PathNode.id).asc()
            )
        )
        return list((await self.session.exec(stmt)).all())

    async def get_node_tutorials(
        self, node_id: int
    ) -> list[PathNodeTutorial]:
        stmt = (
            select(PathNodeTutorial)
            .where(PathNodeTutorial.node_id == node_id)
            .order_by(
                col(PathNodeTutorial.version_no).asc(),
                col(PathNodeTutorial.id).asc(),
            )
        )
        return list((await self.session.exec(stmt)).all())

    async def get_node_resources(
        self, node_id: int
    ) -> list[PathNodeResource]:
        stmt = (
            select(PathNodeResource)
            .where(PathNodeResource.node_id == node_id)
            .order_by(
                col(PathNodeResource.created_at).asc(),
                col(PathNodeResource.id).asc(),
            )
        )
        return list((await self.session.exec(stmt)).all())

    async def get_current_tutorial(
        self, node_id: int
    ) -> PathNodeTutorial | None:
        stmt = (
            select(PathNodeTutorial)
            .where(
                PathNodeTutorial.node_id == node_id,
                PathNodeTutorial.is_current.is_(True),
            )
            .order_by(col(PathNodeTutorial.version_no).desc())
        )
        return (await self.session.exec(stmt)).first()

    async def get_primary_tutorial(
        self, node_id: int
    ) -> PathNodeTutorial | None:
        stmt = (
            select(PathNodeTutorial)
            .where(
                PathNodeTutorial.node_id == node_id,
                PathNodeTutorial.tutorial_type == "primary",
            )
            .order_by(col(PathNodeTutorial.version_no).asc())
        )
        return (await self.session.exec(stmt)).first()

    async def get_latest_round(self, node_id: int) -> int:
        stmt = select(PathNodeQuestion).where(
            PathNodeQuestion.node_id == node_id
        )
        questions = list((await self.session.exec(stmt)).all())
        return max((q.round_no for q in questions), default=0)

    async def get_round_questions(
        self, node_id: int, round_no: int
    ) -> list[PathNodeQuestion]:
        stmt = (
            select(PathNodeQuestion)
            .where(
                PathNodeQuestion.node_id == node_id,
                PathNodeQuestion.round_no == round_no,
            )
            .order_by(col(PathNodeQuestion.question_no).asc())
        )
        return list((await self.session.exec(stmt)).all())

    async def get_profile_dict(
        self, user_id: int
    ) -> dict[str, Any]:
        try:
            profile = await self.profile_builder.get_or_create_global_profile(
                user_id=user_id
            )
            return (
                profile.profile_json
                if profile and profile.profile_json
                else {}
            )
        except ProgrammingError as exc:
            logger.warning(
                "[PathService] 画像表暂不可用，路径规划降级为空画像: "
                "user_id=%s error=%s",
                user_id,
                exc,
            )
            return {}

    async def get_user_learning_profile(self, user_id: int) -> str:
        try:
            return await self.profile_builder.get_profile_markdown(user_id)
        except ProgrammingError as exc:
            logger.warning(
                "[PathService] 画像文本暂不可用，教程生成降级无画像: "
                "user_id=%s error=%s",
                user_id,
                exc,
            )
            return ""

    async def _archive_active_paths(
        self,
        user_id: int,
        module: str,
        exclude_path_id: int | None = None,
    ) -> None:
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

    async def get_active_path_record(
        self, user_id: int, module: str = "mentor"
    ) -> LearningPath | None:
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

    async def _build_path_response(
        self, path: LearningPath
    ) -> LearningPathOverviewResponse:
        nodes = await self._get_nodes_for_path(path.id)
        return LearningPathOverviewResponse(
            id=path.id,
            module=path.module,
            title=path.title,
            goal=path.goal,
            topic=path.topic,
            overall_progress=path.overall_progress,
            status=path.status,
            current_node_key=path.current_node_key,
            stages=list(path.stages_json or []),
            nodes=[LearningPathNodeDTO.from_model(n) for n in nodes],
            created_at=(
                path.created_at.isoformat() if path.created_at else ""
            ),
            updated_at=(
                path.updated_at.isoformat() if path.updated_at else ""
            ),
        )

    async def get_path_active_minutes(
        self, *, user_id: int, path_id: int
    ) -> int:
        stmt = select(LearningSession).where(
            LearningSession.user_id == user_id,
            LearningSession.path_id == path_id,
        )
        sessions = list((await self.session.exec(stmt)).all())
        return sum(
            item.duration_seconds or 0 for item in sessions
        ) // 60

    async def get_current_path_node(
        self, path_id: int, current_node_key: str | None
    ) -> PathNode | None:
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


async def run_generation_bg(
    user_id: int,
    path_id: int,
    request: CreateLearningPathRequest,
    run_id: str,
):
    async with session_scope() as session:
        service = PathService(session)
        await service.run_generation(path_id, user_id, request, run_id)
