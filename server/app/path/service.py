"""路径规划业务逻辑层。

职责：
1. 路径创建、持久化、后台生成编排
2. 路径查询（激活路径、历史列表、详情）
3. 节点工作区构建（教程、资源、测验状态）
4. 节点学习流程（教程生成、测验评分、进度推进）
5. 辅助资源生成与获取
6. 学习事件记录与评估汇总

主要方法分组：
- create_path / run_generation — 路径创建与后台生成
- get_active_path_overview / get_path_by_id / list_path_history — 路径查询
- get_node_workspace / start_learning / generate_tutorial — 节点学习入口
- generate_node_questions / submit_node_quiz — 测验流程
- generate_node_resource / get_node_resource_by_type — 辅助资源
- record_learning_event / get_learning_evaluation — 学习事件与评估
"""

from __future__ import annotations

import asyncio
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import ProgrammingError
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import PATH_QUIZ_SIZE
from app.evaluation.request import LearningEventCreate
from app.evaluation.service import EvaluationService
from app.infra.database import session_scope
from app.path.event import PathEvents
from app.infra.logging import get_logger
from app.infra.models import (
    LearningEvent,
    LearningPath,
    LearningSession,
    PathNode,
    PathNodeQuestion,
    PathNodeResource,
    PathNodeTutorial,
    User,
)
from app.path.schemas import (
    LearningPlan,
    PathRequest,
    PathResourceRequest,
    LearningPathHistoryItem,
    LearningPathNodeDTO,
    LearningPathNodeWorkspaceResponse,
    PathResponse,
    LearningPathQuestionDTO,
    LearningPathResourceDTO,
    PathResourceTaskResponse,
    LearningPathTutorialDTO,
    LearningSignalSnapshot,
    PathLearningEventItem,
    PathLearningEvaluationResponse,
    PathQuizRoundResponse,
    PathQuizSubmitRequest,
    PathQuizSubmitResponse,
    LearnState,
    validate_path_plan,
)
from app.path.workflows import (
    PathPlannerAgent,
    repair_plan,
    get_learn_workflow,
    ACTIVE_NODE_STATUSES,
    COMPLETED_NODE_STATUSES,
)
from app.profile.service import get_profile_service


logger = get_logger(__name__)

# 辅助资源类型集合
AUX_RESOURCE_TYPES = {"mindmap", "code", "reading", "ppt", "cartoon"}

# 节点状态常量
STARTED_NODE_STATUSES = {"in_progress"}
ACCESSIBLE_NODE_STATUSES = ACTIVE_NODE_STATUSES | COMPLETED_NODE_STATUSES
RESOURCE_READY_NODE_STATUSES = STARTED_NODE_STATUSES | COMPLETED_NODE_STATUSES
QUIZ_SUBMIT_NODE_STATUSES = STARTED_NODE_STATUSES

_node_tutorial_locks: dict[int, asyncio.Lock] = {}
_node_question_locks: dict[int, asyncio.Lock] = {}


class PathService:
    """路径规划业务服务类。

    封装路径生成、节点管理、测验评分、资源生成等核心业务逻辑。
    通过 LangGraph 工作流编排节点学习流程。
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.profile_builder = get_profile_service()
        self.path_planner = PathPlannerAgent()
        self.evaluation_service = EvaluationService()
        self.learn_graph = get_learn_workflow()
        # 预创建资源生成服务实例，避免重复实例化
        self._resource_services = self._init_resource_services()

    # ── 路径规划 ────────────────────────────────────────────────────────────

    # 创建学习路径记录，返回新路径 ID
    async def create_path(self, user_id: int, request: PathRequest) -> int:
        """创建学习路径任务，返回路径 ID。"""
        logger.info("[PathService] 创建路径任务: user_id=%s goal=%s", user_id, request.goal[:50])
        path = LearningPath(
            user_id=user_id,
            title=request.topic or "学习路径",
            goal=request.goal,
            topic=request.topic or None,
            current_knowledge=request.current_knowledge,
            preferences=request.preferences.model_dump(mode="json"),
            overall_progress=0,
            status="generating",
            stages_json=[],
        )
        self.session.add(path)
        await self.session.commit()
        await self.session.refresh(path)
        return path.id

    # 持久化路径规划结果：校验、创建节点、更新路径状态
    async def _save_plan(self, path_id: int, user_id: int, plan: LearningPlan) -> None:
        """持久化路径规划结果到数据库。"""
        logger.info("[PathService] 保存路径规划: path_id=%s nodes=%d", path_id, len(plan.nodes))
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

    # 后台路径生成：调用 Agent 规划并推送 SSE 进度事件
    async def run_generation(self, path_id: int, user_id: int, request: PathRequest, run_id: str) -> None:
        """后台路径生成任务 — 调用 PathPlannerAgent 生成并持久化。"""
        logger.info("[PathService] 开始后台路径生成: path_id=%s user_id=%s", path_id, user_id)
        events = PathEvents(user_id=user_id, path_id=path_id, run_id=run_id)
        await events.open()

        async def progress_cb(status: str, progress: int, message: str):
            await events.send(
                event="structure.running",
                message=message,
                progress=progress,
            )

        try:
            await events.send(event="planning.started", message="路径规划已开始")
            profile = await self._get_profile_dict(user_id)
            profile_md = await self.get_user_learning_profile(user_id)
            await events.send(
                event="profile.loaded",
                message="正在初始化路径推演引擎",
                progress=10,
            )

            from app.evaluation.guidance import get_effective_guidance_strategy
            guidance_strategy = await get_effective_guidance_strategy(self.session, user_id)
            plan = await self.path_planner.generate_plan(
                request,
                profile,
                progress_callback=progress_cb,
                profile_markdown=profile_md,
                guidance_strategy=guidance_strategy,
            )

            await events.send(
                event="structure.running",
                message="正在生成节点结构",
                progress=85,
            )

            plan = repair_plan(
                plan=plan,
                macro_stages=list(getattr(plan, "stages", []) or []),
                request=request,
            )

            validate_path_plan(plan)
            await self._save_plan(path_id, user_id, plan)

            await events.send(event="planning.completed", message="路径规划完成", progress=100)
        except Exception as exc:
            logger.error(f"路径规划任务异常: {exc}", exc_info=True)
            path = await self.session.get(LearningPath, path_id)
            if path:
                path.status = "failed"
                await self.session.commit()
            await events.send(
                event="planning.failed",
                message="暂时无法完成本次路径规划",
                progress=0,
            )

    # ── 路径查询 ────────────────────────────────────────────────────────────

    # 获取用户所有可继续学习的路径概览
    async def list_active_path_overviews(self, user_id: int, module: str = "mentor") -> list[PathResponse]:
        """获取用户所有可继续学习的路径概览。"""
        paths = await self._get_active_paths(user_id, module)
        return [await self._build_response(path) for path in paths]

    # 获取最近更新的可继续学习路径概览
    async def get_latest_active_path_overview(self, user_id: int, module: str = "mentor") -> PathResponse | None:
        """获取最近更新的可继续学习路径概览。"""
        path = await self._get_latest_active_path(user_id, module)
        if path is None:
            return None
        return await self._build_response(path)

    # 按 ID 获取路径详情（含所有权校验）
    async def get_path_by_id(
        self, user_id: int, path_id: int
    ) -> PathResponse:
        path = await self._must_get_path(user_id, path_id)
        return await self._build_response(path)

    # 列出用户所有路径历史记录
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

    # 继续学习一条历史路径，不影响其他未完成路径
    async def activate_history_path(
        self, user_id: int, path_id: int
    ) -> PathResponse:
        path = await self._must_get_path(user_id, path_id)
        if path.status in {"failed", "generating"}:
            raise ValueError("该学习路径当前不可继续学习")
        if path.status != "completed":
            path.status = "active"
        path.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        return await self._build_response(path)

    # ── 节点工作区 ──────────────────────────────────────────────────────────

    # 构建节点工作区响应（教程、资源、测验状态）
    async def get_node_workspace(self, user_id: int, node_id: int) -> LearningPathNodeWorkspaceResponse:
        """构建节点工作区响应 — 包含教程、资源、测验状态。"""
        node = await self._must_get_node(user_id, node_id)
        self._ensure_node_accessible(node)
        return await self._build_workspace_response(node)

    # 标记节点开始学习，记录学习事件
    async def start_learning(self, user_id: int, node_id: int) -> PathResponse:
        """标记节点开始学习（轻量，不生成教程）。"""
        logger.info("[PathService] 开始节点学习: user_id=%s node_id=%s", user_id, node_id)
        node = await self._must_get_node(user_id, node_id)
        self._ensure_node_accessible(node)

        if node.status == "available":
            node.status = "in_progress"
            node.started_at = datetime.now(timezone.utc)
            await self.session.commit()

        path = await self._must_get_path(user_id, node.path_id)
        try:
            from app.path.events import record_node_started_event

            await record_node_started_event(
                db=self.session,
                user_id=user_id,
                path_id=path.id,
                path_node_id=node.id,
                node_id=node.node_id,
                course=path.title,
                topic=node.title,
            )
        except Exception:
            logger.exception(
                "Failed to record node_started event: user_id=%s node_id=%s",
                user_id,
                node_id,
            )
        return await self._build_response(path)

    # 生成节点教程（幂等，已有则跳过）
    async def generate_tutorial(self, user_id: int, node_id: int) -> LearningPathNodeWorkspaceResponse:
        """为节点生成教程（耗时操作，独立 API）。

        幂等保证：如果该节点已有 current tutorial，直接返回工作区而不会重复生成。
        这防止了前端重复点击、页面刷新重入、或 PathPlanOverview + PathNodeStudy
        同时触发生成时产生重复教程。
        """
        logger.info("[PathService] 生成节点教程: user_id=%s node_id=%s", user_id, node_id)
        node = await self._must_get_node(user_id, node_id)
        self._ensure_node_accessible(node)

        lock = _node_tutorial_locks.setdefault(node.id, asyncio.Lock())
        async with lock:
            tutorials = await self._get_node_tutorials(node.id)
            current = next((t for t in tutorials if t.is_current), None)

            if current is not None:
                logger.info(
                    "[PathService] 节点已有教程(id=%d)，跳过生成，直接返回工作区",
                    current.id,
                )
                return await self._build_workspace_response(node)

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

            node = await self._must_get_node(user_id, node_id)
            return await self._build_workspace_response(node)

    # 聚合节点工作区数据（教程、资源、测验轮次）
    async def _build_workspace_response(
        self, node: PathNode
    ) -> LearningPathNodeWorkspaceResponse:
        path = await self._must_get_path(node.user_id, node.path_id)
        tutorials = await self._get_node_tutorials(node.id)
        current = next((t for t in tutorials if t.is_current), None)
        resources = await self._get_node_resources(node.id)
        overview = await self._build_response(path)
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
            quiz_available=await self._has_quiz_questions(node.id),
        )

    # 创建节点辅助资源生成任务（思维导图/代码/PPT/阅读/动画）
    async def create_node_resource_task(
        self,
        user_id: int,
        node_id: int,
        resource_type: str,
        run_id: str,
    ) -> PathResourceTaskResponse:
        """创建节点辅助资源生成任务，后台完成实际生成。"""
        logger.info(
            "[PathService] 创建节点资源任务: user_id=%s node_id=%s type=%s run_id=%s",
            user_id, node_id, resource_type, run_id,
        )
        if resource_type not in AUX_RESOURCE_TYPES:
            raise ValueError(f"不支持的资源类型: {resource_type}")

        node = await self._must_get_node(user_id, node_id)
        self._ensure_node_accessible(node)
        self._ensure_node_resource_ready(node)

        current_tutorial = await self._get_current_tutorial(node.id)
        if current_tutorial is None:
            raise ValueError("当前节点还没有教程，请先生成主教程再生成辅助资源")

        version_no = await self._count_resources(node.id, resource_type) + 1
        resource = PathNodeResource(
            path_id=node.path_id,
            node_id=node.id,
            tutorial_id=current_tutorial.id,
            user_id=user_id,
            resource_type=resource_type,
            version_no=version_no,
            title=f"{node.title} - {resource_type}",
            content_format={"ppt": "html", "cartoon": "mp4"}.get(resource_type, "markdown"),
            status="generating",
            input_json={"run_id": run_id},
        )
        self.session.add(resource)
        await self.session.commit()
        await self.session.refresh(resource)
        return PathResourceTaskResponse(
            resource=LearningPathResourceDTO.from_model(resource),
            run_id=run_id,
        )

    async def _call_generate_for_path(
        self,
        resource_type: str,
        request: PathResourceRequest,
    ) -> "AgentResult":
        """统一调用各服务的 generate_for_path 接口。"""
        logger.info(
            "[PathService] 调用资源生成服务: type=%s node_id=%s node_title=%s",
            resource_type, request.node_id, request.node_title,
        )
        services = self._resource_services
        if resource_type == "ppt":
            logger.info("[PathService] 调用 PPTService.generate_for_path")
            return await services["ppt"].generate_for_path(request)
        elif resource_type == "cartoon":
            logger.info("[PathService] 调用 PathCartoonAdapter.generate")
            return await services["cartoon"].generate(request)
        elif resource_type == "mindmap":
            logger.info("[PathService] 调用 MindmapAgent.generate_for_path")
            return await services["mindmap"].generate_for_path(request)
        elif resource_type == "code":
            logger.info("[PathService] 调用 CodeAgent.generate_for_path")
            return await services["code"].generate_for_path(request)
        elif resource_type == "reading":
            logger.info("[PathService] 调用 ReadingAgent.generate_for_path")
            return await services["reading"].generate_for_path(request)
        raise ValueError(f"不支持的资源类型: {resource_type}")

    @staticmethod
    def _init_resource_services() -> dict:
        """预创建资源生成服务实例。"""
        from app.shared.ppt import PPTService
        from app.path.cartoon import PathCartoonAdapter
        from app.resource.agents import AGENT_REGISTRY
        return {
            "ppt": PPTService(),
            "cartoon": PathCartoonAdapter(),
            "mindmap": AGENT_REGISTRY["mindmap"](),
            "code": AGENT_REGISTRY["code"](),
            "reading": AGENT_REGISTRY["reading"](),
        }

    # 获取节点指定类型的最新资源
    async def get_node_resource_by_type(self, user_id: int, node_id: int, resource_type: str) -> LearningPathResourceDTO | None:
        """获取节点指定类型的最新资源（用于复习回看）。"""
        if resource_type not in AUX_RESOURCE_TYPES:
            raise ValueError(f"不支持的资源类型: {resource_type}")
        node = await self._must_get_node(user_id, node_id)
        self._ensure_node_accessible(node)

        stmt = (
            select(PathNodeResource)
            .where(
                PathNodeResource.node_id == node.id,
                PathNodeResource.resource_type == resource_type,
                PathNodeResource.status == "completed",
            )
            .order_by(col(PathNodeResource.version_no).desc())
        )
        resource = (await self.session.exec(stmt)).first()
        if resource is None:
            return None
        return LearningPathResourceDTO.from_model(resource)

    # ── 测验 ────────────────────────────────────────────────────────────────

    # 获取最新一轮已有测验题目（不重新生成）
    async def get_node_questions(self, user_id: int, node_id: int) -> PathQuizRoundResponse | None:
        """获取最新一轮已有测验题目（不重新生成）。无题目时返回 None。"""
        logger.info("[PathService] 获取已有测验题目: user_id=%s node_id=%s", user_id, node_id)
        node = await self._must_get_node(user_id, node_id)
        self._ensure_node_accessible(node)

        round_no = await self._get_latest_round(node.id)
        if round_no == 0:
            return None

        questions = await self._get_round_questions(node.id, round_no)
        if not questions:
            return None

        current_tutorial = await self._get_current_tutorial(node.id)
        return PathQuizRoundResponse(
            node_id=node.id,
            tutorial_id=current_tutorial.id if current_tutorial else None,
            round_no=round_no,
            questions=[LearningPathQuestionDTO.from_model(q) for q in questions],
        )

    # 生成节点测验题目，调用 LLM 生成 5 道选择题
    async def generate_node_questions(self, user_id: int, node_id: int) -> PathQuizRoundResponse:
        """生成节点测验题目 — 5 道选择题。"""
        logger.info("[PathService] 生成测验题目: user_id=%s node_id=%s", user_id, node_id)
        node = await self._must_get_node(user_id, node_id)
        self._ensure_node_accessible(node)
        self._ensure_node_quiz_ready(node)

        lock = _node_question_locks.setdefault(node.id, asyncio.Lock())
        async with lock:
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

    # 提交测验答案，评分并推进节点状态
    async def submit_node_quiz(self, user_id: int, node_id: int, payload: PathQuizSubmitRequest) -> PathQuizSubmitResponse:
        """提交测验答案并评分，决定节点下一步状态。"""
        logger.info("[PathService] 提交测验: user_id=%s node_id=%s answers=%d", user_id, node_id, len(payload.answers))
        node = await self._must_get_node(user_id, node_id)
        self._ensure_node_accessible(node)
        self._ensure_node_quiz_ready(node)

        round_no = await self._get_latest_round(node.id)
        if round_no == 0:
            raise ValueError("当前节点还没有测验题")
        questions = await self._get_round_questions(node.id, round_no)
        self._validate_quiz_submission(questions, payload)

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

    # 计算路径学习效果评估（得分、薄弱点、优化建议）
    async def get_learning_evaluation(self, user_id: int, path_id: int) -> PathLearningEvaluationResponse | None:
        """计算路径学习效果评估。"""
        path = await self._must_get_path(user_id, path_id)
        stmt = (
            select(LearningEvent)
            .where(
                LearningEvent.user_id == user_id,
                LearningEvent.module == "path",
                LearningEvent.entity_id == str(path.id),
            )
            .order_by(col(LearningEvent.created_at).desc())
            .limit(50)
        )
        events = list((await self.session.exec(stmt)).all())
        active_minutes = await self._get_path_active_minutes(
            user_id=user_id, path_id=path.id
        )
        signal_snapshot = build_path_signal_snapshot(events, active_minutes)
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

    # 记录学习事件并校验节点归属路径
    async def record_learning_event(
        self,
        user_id: int,
        path_id: int,
        payload: LearningEventCreate,
    ) -> LearningEvent:
        path = await self._must_get_path(user_id, path_id)
        meta = dict(payload.event_metadata or {})
        meta["path_id"] = path.id
        path_node_id = meta.get("path_node_id") or payload.path_node_id
        if path_node_id is not None:
            node = await self._must_get_node(user_id, int(path_node_id))
            if node.path_id != path.id:
                raise ValueError("学习事件节点不属于当前学习路径")
            meta["path_node_id"] = node.id
            meta["node_id"] = node.node_id
        payload = payload.model_copy(update={
            "path_id": path.id,
            "path_node_id": meta.get("path_node_id"),
            "node_id": meta.get("node_id"),
            "entity_id": str(path.id),
            "event_metadata": meta,
        })
        record_result = await self.evaluation_service.record_event(
            self.session,
            user_id=user_id,
            payload=payload,
        )
        event = record_result[0] if isinstance(record_result, tuple) else record_result
        return event

    # ── 共享内部方法 ────────────────────────────────────────────────────────

    # 获取路径并验证所有权，不存在时抛 ValueError
    async def _must_get_path(self, user_id: int, path_id: int) -> LearningPath:
        """获取路径并验证所有权，不存在时抛出 ValueError。"""
        path = await self.session.get(LearningPath, path_id)
        if path is None or path.user_id != user_id:
            raise ValueError("学习路径不存在")
        return path

    # 获取节点并验证所有权，不存在时抛 ValueError
    async def _must_get_node(self, user_id: int, node_id: int) -> PathNode:
        node = await self.session.get(PathNode, node_id)
        if node is None or node.user_id != user_id:
            raise ValueError("路径节点不存在")
        return node

    # 校验节点已解锁可访问
    def _ensure_node_accessible(self, node: PathNode) -> None:
        if node.status not in ACCESSIBLE_NODE_STATUSES:
            raise ValueError("路径节点尚未解锁")

    # 校验节点已进入可生成资源阶段
    def _ensure_node_resource_ready(self, node: PathNode) -> None:
        if node.status not in RESOURCE_READY_NODE_STATUSES:
            raise ValueError("请先进入深入学习，再生成该节点的学习资源")

    # 校验节点可进行正式测验
    def _ensure_node_quiz_ready(self, node: PathNode) -> None:
        if node.status not in QUIZ_SUBMIT_NODE_STATUSES:
            raise ValueError("该节点当前不能提交或生成正式测验")

    def _validate_quiz_submission(
        self,
        questions: list[PathNodeQuestion],
        payload: PathQuizSubmitRequest,
    ) -> None:
        """校验测验提交必须完整、唯一、属于当前轮且未提交过。"""
        if len(questions) != PATH_QUIZ_SIZE:
            raise ValueError("当前节点还没有完整的五道题")
        if any(question.submitted_at is not None for question in questions):
            raise ValueError("当前轮次已经提交，不能重复提交")

        expected_ids = {int(question.id) for question in questions if question.id is not None}
        submitted_ids = [answer.question_id for answer in payload.answers]
        if len(set(submitted_ids)) != len(submitted_ids):
            raise ValueError("不能重复提交同一道题")
        if set(submitted_ids) != expected_ids:
            raise ValueError("提交答案必须对应当前轮次的全部题目")
        if any(not answer.response.strip() for answer in payload.answers):
            raise ValueError("答案不能为空")

    # 获取路径下全部节点（按优先级排序）
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

    # 获取节点全部教程（按版本号排序）
    async def _get_node_tutorials(
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

    # 获取节点全部辅助资源
    async def _get_node_resources(
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

    # 获取节点当前激活的教程
    async def _get_current_tutorial(
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

    # 获取节点主教程（primary 类型，最早版本）
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

    # 获取节点最新测验轮次编号
    async def _get_latest_round(self, node_id: int) -> int:
        stmt = select(PathNodeQuestion).where(
            PathNodeQuestion.node_id == node_id
        )
        questions = list((await self.session.exec(stmt)).all())
        return max((q.round_no for q in questions), default=0)

    # 检查节点是否已有完整一轮测验题目
    async def _has_quiz_questions(self, node_id: int) -> bool:
        """检查节点是否已有测验题目（至少一轮完整 5 道题）。"""
        round_no = await self._get_latest_round(node_id)
        if round_no == 0:
            return False
        questions = await self._get_round_questions(node_id, round_no)
        return len(questions) >= PATH_QUIZ_SIZE

    # 获取指定轮次的测验题目
    async def _get_round_questions(
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

    # 获取用户画像数据（维度 + 基础信息）
    async def _get_profile_dict(
        self, user_id: int
    ) -> dict[str, Any]:
        """获取用户画像数据（维度 + 基础信息）。"""
        try:
            from app.infra.models import User
            user = (await self.session.exec(select(User).where(User.id == user_id))).first()
            base_info = {
                "school": user.school or "",
                "school_level": user.school_level or "",
                "major": user.major or "",
                "grade": user.grade or "",
                "daily_study_time": user.daily_study_time or "",
                "global_learning_goal": user.global_learning_goal or "",
                "programming_languages": user.programming_languages or [],
                "courses": user.courses or [],
            } if user else {}

            dimensions = await self.profile_builder.get_dimensions(
                user_id=user_id, db=self.session
            )
            return {
                "base_info": base_info,
                "dimensions": dimensions,
            }
        except (ProgrammingError, AttributeError) as exc:
            logger.warning(
                "[PathService] 画像表暂不可用，路径规划降级为空画像: "
                "user_id=%s error=%s",
                user_id,
                exc,
            )
            return {}

    # 获取用户画像 Markdown 文本（降级为空串）
    async def get_user_learning_profile(self, user_id: int) -> str:
        try:
            return await self.profile_builder.build_profile_markdown(user_id=user_id)
        except ProgrammingError as exc:
            logger.warning(
                "[PathService] 画像文本暂不可用，教程生成降级无画像: "
                "user_id=%s error=%s",
                user_id,
                exc,
            )
            return ""

    # 归档用户当前所有激活路径（可排除指定路径）
    async def _archive_active(
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

    # 查询用户所有可继续学习路径（最近更新优先）
    async def _get_active_paths(
        self, user_id: int, module: str = "mentor"
    ) -> list[LearningPath]:
        stmt = (
            select(LearningPath)
            .where(
                LearningPath.user_id == user_id,
                LearningPath.module == module,
                LearningPath.status == "active",
                LearningPath.overall_progress < 100,
            )
            .order_by(col(LearningPath.updated_at).desc())
        )
        return list((await self.session.exec(stmt)).all())

    # 查询用户最近更新的可继续学习路径
    async def _get_latest_active_path(
        self, user_id: int, module: str = "mentor"
    ) -> LearningPath | None:
        paths = await self._get_active_paths(user_id, module)
        return paths[0] if paths else None

    # 组装路径概览响应（含所有节点 DTO）
    async def _build_response(
        self, path: LearningPath
    ) -> PathResponse:
        nodes = await self._get_nodes_for_path(path.id)
        return PathResponse(
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

    # 汇总路径的有效学习时长（分钟）
    # 汇总路径的有效学习时长（分钟）
    async def _get_path_active_minutes(
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

    # 根据 current_node_key 获取路径当前节点
    async def _get_current_path_node(
        self, path_id: int, current_node_key: str | None
    ) -> PathNode | None:
        if not current_node_key:
            return None
        stmt = select(PathNode).where(
            PathNode.path_id == path_id,
            PathNode.node_id == current_node_key,
        )
        return (await self.session.exec(stmt)).first()

    # 将阶段对象归一化为 JSON 字典
    def _stage_to_dict(self, stage: Any) -> dict[str, Any]:
        if hasattr(stage, "model_dump"):
            return stage.model_dump(mode="json")
        return dict(stage)

    async def complete_resource_task(
        self,
        *,
        user_id: int,
        resource_id: int,
        run_id: str,
    ) -> None:
        """执行资源生成任务并更新任务记录。"""
        logger.info(
            "[PathService] 开始执行资源生成任务: user_id=%s resource_id=%s run_id=%s",
            user_id, resource_id, run_id,
        )
        events = PathEvents(user_id=user_id, path_id=resource_id, run_id=run_id)
        await events.open()
        resource = await self.session.get(PathNodeResource, resource_id)
        if resource is None or resource.user_id != user_id:
            logger.error(
                "[PathService] 资源任务不存在或无权限: resource_id=%s user_id=%s",
                resource_id, user_id,
            )
            await events.send(event="resource.failed", message="资源任务不存在", progress=0)
            return

        resource_type = resource.resource_type
        logger.info(
            "[PathService] 资源任务信息: resource_id=%s type=%s node_id=%s status=%s",
            resource_id, resource_type, resource.node_id, resource.status,
        )

        await events.send(
            event="resource.started",
            message="资源生成任务已开始",
            progress=5,
            data={"resource_id": resource_id, "resource_type": resource_type},
        )
        try:
            node = await self._must_get_node(user_id, resource.node_id)
            self._ensure_node_accessible(node)
            self._ensure_node_resource_ready(node)
            tutorial = await self._get_current_tutorial(node.id)
            if tutorial is None:
                raise ValueError("当前节点还没有教程，请先生成主教程再生成辅助资源")
            logger.info(
                "[PathService] 构建资源生成请求: node_id=%s tutorial_id=%s type=%s",
                node.id, tutorial.id, resource_type,
            )
            request = await self._build_resource_request(user_id, node, tutorial)
            await events.send(event="resource.running", message="正在调用资源智能体", progress=35)
            logger.info(
                "[PathService] 调用资源生成服务: type=%s node_title=%s",
                resource_type, node.title,
            )
            result = await self._call_generate_for_path(resource_type, request)
            logger.info(
                "[PathService] 资源生成完成: type=%s success=%s title=%s",
                resource_type, result.success, result.title,
            )
            await self._apply_resource_result(resource, tutorial, result)
            await events.send(
                event="resource.completed" if result.success else "resource.failed",
                message="资源生成完成" if result.success else (result.error or "资源生成失败"),
                progress=100,
                data={"resource_id": resource.id, "status": resource.status},
            )
        except Exception as exc:
            logger.error(
                "[PathService] 路径节点资源任务异常: resource_id=%s type=%s error=%s",
                resource_id, resource_type, exc, exc_info=True,
            )
            resource.status = "failed"
            resource.error_message = str(exc)
            resource.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            await events.send(
                event="resource.failed",
                message=str(exc) or "资源生成失败",
                progress=100,
                data={"resource_id": resource.id, "status": "failed"},
            )

    async def _build_resource_request(
        self,
        user_id: int,
        node: PathNode,
        tutorial: PathNodeTutorial,
    ) -> PathResourceRequest:
        """构建路径节点资源生成请求。"""
        from app.path.schemas import PathPreferences

        path = await self._must_get_path(user_id, node.path_id)
        user = await self.session.get(User, user_id)
        profile = await self._get_profile_dict(user_id)

        # 解析路径偏好参数（使用安全方法处理可能格式错误的数据）
        preferences_data = path.preferences or {}
        preferences = PathPreferences.from_dict_safe(preferences_data)

        return PathResourceRequest(
            user_id=user_id,
            path_id=node.path_id,
            node_id=node.id,
            profile=profile,
            tutorial=LearningPathTutorialDTO.from_model(tutorial),
            username=user.username if user else str(user_id),
            path_title=path.title,
            path_goal=path.goal,
            node_title=node.title,
            node_key=node.node_id,
            difficulty=node.difficulty or "beginner",
            current_knowledge=list(path.current_knowledge or []),
            preferences=preferences,
        )

    async def _apply_resource_result(
        self,
        resource: PathNodeResource,
        tutorial: PathNodeTutorial,
        result: "AgentResult",
    ) -> LearningPathResourceDTO:
        """将资源生成结果写回既有任务记录。"""
        resource.tutorial_id = tutorial.id
        resource.title = result.title if result.success and result.title else resource.title
        resource.content_format = result.file_type or resource.content_format
        resource.content_text = result.content if result.success else None
        resource.status = "completed" if result.success else "failed"
        resource.error_message = None if result.success else result.error
        resource.summary = result.summary if result.success else None
        resource.metadata_json = result.metadata if result.success else None
        resource.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(resource)
        return LearningPathResourceDTO.from_model(resource)


    async def _count_resources(self, node_id: int, resource_type: str) -> int:
        """统计节点指定类型的资源数量。"""
        from sqlalchemy import func

        stmt = select(func.count()).where(
            PathNodeResource.node_id == node_id,
            PathNodeResource.resource_type == resource_type,
        )
        result = await self.session.exec(stmt)
        return result.first() or 0


# 根据路径学习事件构建路径专属学习信号快照
def build_path_signal_snapshot(
    events: list[LearningEvent],
    active_minutes: int,
) -> LearningSignalSnapshot:
    score_values = [event.score for event in events if event.score is not None]
    average_score = round(sum(score_values) / len(score_values), 1) if score_values else None

    weak_counter: Counter[str] = Counter()
    preferred_counter: Counter[str] = Counter()
    for event in events:
        topic = event.topic or event.course
        if event.score is not None and event.score < 70 and topic:
            weak_counter[topic] += 1

        metadata = event.event_metadata or {}
        feedback = str(metadata.get("feedback") or getattr(event, "feedback", "") or "")
        if topic and any(keyword in feedback for keyword in ("太难", "看不懂", "不会", "卡住", "薄弱", "错")):
            weak_counter[topic] += 1
        for keyword, label in {
            "图解": "图解材料",
            "案例": "案例讲解",
            "代码": "代码实操",
            "视频": "视频讲解",
            "题": "练习题库",
        }.items():
            if keyword in feedback:
                preferred_counter[label] += 1

    recommendations: list[str] = []
    if average_score is not None and average_score < 70:
        recommendations.append("优先安排错题复盘和基础讲解资源，降低后续学习坡度。")
    if weak_counter:
        recommendations.append(f"下一轮资源生成应重点覆盖「{weak_counter.most_common(1)[0][0]}」。")
    if preferred_counter:
        recommendations.append(f"资源推送可提高「{preferred_counter.most_common(1)[0][0]}」占比。")
    if not recommendations:
        recommendations.append("继续按当前路径推进，并通过阶段测验积累更多评估信号。")

    return LearningSignalSnapshot(
        average_score=average_score,
        weak_topics=[item for item, _ in weak_counter.most_common(5)],
        preferred_resources=[item for item, _ in preferred_counter.most_common(5)],
        completed_resource_count=0,
        viewed_resource_count=0,
        active_minutes=active_minutes,
        recommendations=recommendations,
    )


# 将 LearningEvent ORM 转换为路径事件响应 DTO
def build_learning_event_item(event: LearningEvent) -> PathLearningEventItem:
    return PathLearningEventItem(
        id=event.id or 0,
        module=event.module or "path",
        entity_id=event.entity_id or (str(getattr(event, "path_id", "")) or None),
        event_type=event.event_type,
        course=event.course,
        topic=event.topic,
        score=event.score,
        event_metadata=event.event_metadata,
        created_at=event.created_at,
    )


# 后台任务入口：独立会话中执行路径生成
async def run_generation_bg(
    user_id: int,
    path_id: int,
    request: PathRequest,
    run_id: str,
):
    async with session_scope() as session:
        service = PathService(session)
        await service.run_generation(path_id, user_id, request, run_id)


# 后台任务入口：独立会话中执行路径节点资源生成
async def run_resource_generation_bg(
    user_id: int,
    resource_id: int,
    run_id: str,
):
    logger.info(
        "[PathBG] 开始后台资源生成: user_id=%s resource_id=%s run_id=%s",
        user_id, resource_id, run_id,
    )
    try:
        async with session_scope() as session:
            service = PathService(session)
            await service.complete_resource_task(
                user_id=user_id,
                resource_id=resource_id,
                run_id=run_id,
            )
        logger.info(
            "[PathBG] 后台资源生成完成: resource_id=%s run_id=%s",
            resource_id, run_id,
        )
    except Exception as exc:
        logger.error(
            "[PathBG] 后台资源生成异常: resource_id=%s run_id=%s error=%s",
            resource_id, run_id, exc, exc_info=True,
        )
