from datetime import datetime, timezone
from typing import Any, Sequence
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.infra.logging import get_logger
from app.memory.service import MemoryService
from app.infra.models import CoursePath, CoursePathGenerationTask, CoursePathNode, CoursePathResourceBinding
from app.path.agents.planner import PathPlannerAgent
from app.path.schemas import (
    CoursePathNodeDTO,
    CoursePathResponse,
    GeneratePathRequest,
    PathGenerationTaskResponse,
    PathPlanFeedbackRequest,
)
from app.path.validation import normalize_path_plan, validate_path_plan
from app.path.signals import get_resource_policy_fallback, build_learning_signal_snapshot
from app.resource.schemas import AgentConfigs, AgentSelection, OutputOptions, ResourceGenerationRequest

logger = get_logger(__name__)

ACTIVE_GENERATION_STATUSES = ("pending", "preparing", "planning", "validating")
PATH_SEARCH_ENABLED_KEY = "_path_enable_search"


def _format_search_evidence(records: list[dict] | str | None) -> list[dict] | None:
    """将结构化搜索证据记录格式化为持久化格式。

    接受 list[dict]（结构化证据）或 str（旧格式纯文本，自动包装）。
    每条记录包含 {tool, query, title, url, snippet, used_for}。
    """
    if not records:
        return None
    if isinstance(records, str):
        text = records.strip()
        if not text:
            return None
        return [{"tool": "unknown", "query": "", "title": "", "url": "", "snippet": text[:500], "used_for": []}]
    cleaned = []
    for r in records:
        cleaned.append({
            "tool": r.get("tool", ""),
            "query": r.get("query", ""),
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("snippet", ""),
            "used_for": r.get("used_for", []),
        })
    return cleaned or None


class CoursePathService:
    """课程路径业务服务层。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.memory_layer = MemoryService()
        self.agent = PathPlannerAgent()

    async def generate_path(self, user_id: int, request: GeneratePathRequest) -> CoursePathResponse:
        """根据用户画像和需求，生成新的课程学习路径，并保存到数据库。

        路径生成仅创建节点，不自动触发资源生成。
        用户需要为每个 available 节点手动触发资源生成。
        """
        logger.info(f"Generating new course path for user_id={user_id}, topic={request.topic}")

        profile_dict = await self._get_profile_dict(user_id)
        plan, search_evidence = await self.agent.generate_plan(
            request=request,
            profile=profile_dict,
        )
        normalize_path_plan(plan)
        validate_path_plan(plan)
        db_path, db_nodes = await self._persist_generated_path(user_id, request, plan, search_evidence=search_evidence)
        return self._build_path_response(db_path, db_nodes)

    async def _get_active_path_record(self, user_id: int, module: str = "mentor") -> CoursePath | None:
        statement = select(CoursePath).where(
            CoursePath.user_id == user_id,
            CoursePath.module == module,
            CoursePath.status == "active"
        ).order_by(CoursePath.created_at.desc())
        return (await self.session.exec(statement)).first()

    async def adjust_path(self, user_id: int, request: PathPlanFeedbackRequest) -> CoursePathResponse:
        """根据反馈和画像动态微调未完成的路径节点。"""
        logger.info(f"Adjusting course path for user_id={user_id}, module=mentor")

        # 1. 获取当前活跃路径
        active_path = await self._get_active_path_record(user_id, "mentor")
        if not active_path:
            raise ValueError("当前没有活跃的学习路径")

        # 2. 读取所有节点并分类
        all_nodes = await self._get_nodes_for_path(active_path.id)
        completed_nodes = [n for n in all_nodes if n.status in ("completed", "in_progress")]
        remaining_nodes = [n for n in all_nodes if n.status not in ("completed", "in_progress")]

        # 3. 读取画像
        profile_dict = await self._get_profile_dict(user_id)
        resource_context = ""
        if request.resource_id is not None:
            resource_context = await self._build_resource_context(
                user_id=user_id,
                resource_id=request.resource_id,
            )

        # 3.5: 读取学习效果摘要
        learning_signal_text = ""
        if request.use_learning_signals:
            try:
                snapshot = await build_learning_signal_snapshot(self.session, user_id, active_path)
                if snapshot.average_score is not None or snapshot.weak_topics:
                    learning_signal_text = (
                        f"\n\n学习效果摘要：平均分数={snapshot.average_score}, "
                        f"薄弱知识点={snapshot.weak_topics}, "
                        f"偏好资源={snapshot.preferred_resources}, "
                        f"负面反馈={snapshot.negative_feedback}, "
                        f"建议={snapshot.recommendations}"
                    )
            except Exception as exc:
                logger.warning("构建学习效果摘要失败: %s", exc)

        # 4. 调用 Agent 重新规划后续节点
        plan = await self.agent.adjust_plan(
            active_path=active_path,
            completed_nodes=completed_nodes,
            remaining_nodes=remaining_nodes,
            profile=profile_dict,
            feedback=request.feedback + learning_signal_text,
            weak_points=request.weak_points or [],
            resource_context=resource_context,
        )
        normalize_path_plan(plan)
        validate_path_plan(plan)

        # 5. 更新数据库
        # 删除所有未完成节点
        for r_node in remaining_nodes:
            await self.session.delete(r_node)
        await self.session.flush()

        # 插入新的规划节点
        completed_node_ids = {n.node_id for n in completed_nodes}
        db_nodes = list(completed_nodes)

        for agent_node in plan.nodes:
            # 过滤掉已经完成的节点（由 completed_node_ids 判定，防止大模型重复输出已完成的）
            if agent_node.node_id in completed_node_ids:
                continue

            db_node = CoursePathNode(
                path_id=active_path.id,
                user_id=user_id,
                node_id=agent_node.node_id,
                stage_id=agent_node.stage_id,
                title=agent_node.title,
                prerequisites=agent_node.prerequisites,
                mastery_target=agent_node.mastery_target,
                estimated_minutes=agent_node.estimated_minutes,
                difficulty=agent_node.difficulty,
                recommendation_reason=agent_node.recommendation_reason,
                priority=agent_node.priority,
                resource_policy=agent_node.resource_policy.model_dump() if agent_node.resource_policy else None,
                status="locked",
                resource_status="not_started",
            )

            # 若前置条件全满足，解锁为 available
            if not agent_node.prerequisites or set(agent_node.prerequisites).issubset(completed_node_ids):
                db_node.status = "available"

            db_nodes.append(db_node)
            self.session.add(db_node)

        # 更新路径主表的元数据
        active_path.title = plan.title
        active_path.eta_days = plan.eta_days
        active_path.confidence = plan.confidence
        active_path.stages_json = [s.model_dump() for s in plan.stages]
        active_path.adjustment_rationale = plan.adjustment_rationale
        active_path.updated_at = datetime.now(timezone.utc)

        await self.session.commit()

        # 6. 返回新的 CoursePathResponse
        resource_map = await self._get_node_resource_ids([n.id for n in db_nodes if n.id is not None])
        return self._build_path_response(active_path, db_nodes, resource_map)

    async def start_generation_task(
        self,
        *,
        user_id: int,
        request: GeneratePathRequest,
    ) -> dict[str, Any]:
        """创建路径生成任务；同模块的进行中任务会被复用，避免重复规划。"""
        statement = (
            select(CoursePathGenerationTask)
            .where(
                CoursePathGenerationTask.user_id == user_id,
                CoursePathGenerationTask.module == request.module,
                col(CoursePathGenerationTask.status).in_(ACTIVE_GENERATION_STATUSES),
            )
            .order_by(col(CoursePathGenerationTask.created_at).desc())
        )
        existing = (await self.session.exec(statement)).first()
        if existing is not None:
            return {
                "task": self._build_task_response(existing),
                "should_schedule": False,
            }

        task = CoursePathGenerationTask(
            user_id=user_id,
            module=request.module,
            goal=request.goal,
            topic=request.topic,
            current_knowledge=request.current_knowledge,
            preferences=self._encode_task_preferences(request),
        )
        self.session.add(task)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(task)
        return {
            "task": self._build_task_response(task),
            "should_schedule": True,
        }

    async def get_generation_task(self, *, user_id: int, task_id: int) -> PathGenerationTaskResponse | None:
        statement = select(CoursePathGenerationTask).where(
            CoursePathGenerationTask.id == task_id,
            CoursePathGenerationTask.user_id == user_id,
        )
        task = (await self.session.exec(statement)).first()
        return self._build_task_response(task) if task is not None else None

    async def get_active_generation_task(
        self,
        *,
        user_id: int,
        module: str = "mentor",
    ) -> PathGenerationTaskResponse | None:
        statement = (
            select(CoursePathGenerationTask)
            .where(
                CoursePathGenerationTask.user_id == user_id,
                CoursePathGenerationTask.module == module,
                col(CoursePathGenerationTask.status).in_(ACTIVE_GENERATION_STATUSES),
            )
            .order_by(col(CoursePathGenerationTask.created_at).desc())
        )
        task = (await self.session.exec(statement)).first()
        return self._build_task_response(task) if task is not None else None

    async def execute_generation_task(self, task_id: int) -> None:
        """在后台执行路径规划，并在每个真实边界持久化进度。"""
        logger.info("[PathService] 开始执行路径规划任务: task_id=%s", task_id)
        task = await self.session.get(CoursePathGenerationTask, task_id)
        if task is None or task.status not in ACTIVE_GENERATION_STATUSES:
            logger.warning("[PathService] 任务不存在或状态不匹配: task_id=%s", task_id)
            return

        try:
            await self._set_task_progress(task, "preparing", 15, "正在读取学习画像与目标上下文")
            profile_dict = await self._get_profile_dict(task.user_id)
            request = GeneratePathRequest(
                goal=task.goal,
                topic=task.topic,
                module=task.module,
                current_knowledge=task.current_knowledge or [],
                preferences=self._decode_user_preferences(task.preferences or {}),
                enable_search=self._decode_search_enabled(task.preferences or {}),
            )
            await self._set_task_progress(task, "planning", 30, "路径规划智能体正在检索参考资料并编排学习节点")
            plan, search_evidence = await self.agent.generate_plan(
                request=request,
                profile=profile_dict,
            )
            logger.info("[PathService] 规划完成: task_id=%s nodes=%d", task_id, len(plan.nodes))
            await self._set_task_progress(task, "validating", 80, "正在校验依赖关系并保存学习地图")
            normalize_path_plan(plan)
            validate_path_plan(plan)
            db_path, _ = await self._persist_generated_path(user_id=task.user_id, request=request, plan=plan, search_evidence=search_evidence, commit=False)
            task.generated_path_id = db_path.id
            task.status = "completed"
            task.progress = 100
            task.latest_message = "专属学习路径已生成"
            task.error_message = None
            task.completed_at = datetime.now(timezone.utc)
            task.updated_at = task.completed_at
            await self.session.commit()
            logger.info("[PathService] 路径规划任务完成: task_id=%s path_id=%s", task_id, db_path.id)
        except Exception as exc:
            await self.session.rollback()
            failed_task = await self.session.get(CoursePathGenerationTask, task_id)
            if failed_task is not None:
                failed_task.status = "failed"
                failed_task.latest_message = "路径规划失败，请稍后重试"
                failed_task.error_message = str(exc)
                failed_task.completed_at = datetime.now(timezone.utc)
                failed_task.updated_at = failed_task.completed_at
                await self.session.commit()
            logger.exception("[PathService] 路径规划任务失败: task_id=%s err=%s", task_id, exc)

    async def _get_profile_dict(self, user_id: int) -> dict[str, Any]:
        profile = await self.memory_layer.get_or_create_profile(user_id)
        return profile.profile_json if profile and profile.profile_json else {}

    def _encode_task_preferences(self, request: GeneratePathRequest) -> dict[str, Any]:
        preferences = dict(request.preferences or {})
        preferences[PATH_SEARCH_ENABLED_KEY] = request.enable_search
        return preferences

    def _decode_user_preferences(self, preferences: dict[str, Any]) -> dict[str, Any]:
        cleaned = dict(preferences or {})
        cleaned.pop(PATH_SEARCH_ENABLED_KEY, None)
        return cleaned

    def _decode_search_enabled(self, preferences: dict[str, Any]) -> bool:
        value = dict(preferences or {}).get(PATH_SEARCH_ENABLED_KEY, True)
        return bool(value)

    async def _set_task_progress(
        self,
        task: CoursePathGenerationTask,
        status: str,
        progress: int,
        latest_message: str,
    ) -> None:
        now = datetime.now(timezone.utc)
        task.status = status
        task.progress = progress
        task.latest_message = latest_message
        task.updated_at = now
        if task.started_at is None:
            task.started_at = now
        await self.session.commit()

    async def _persist_generated_path(
        self,
        user_id: int,
        request: GeneratePathRequest,
        plan: Any,
        *,
        search_evidence: list[dict] | None = None,
        commit: bool = True,
    ) -> tuple[CoursePath, list[CoursePathNode]]:
        """持久化已验证路径；后台任务在最终提交前同时完成任务状态更新。"""
        await self._archive_active_paths(user_id, request.module)

        db_path = CoursePath(
            user_id=user_id,
            module=request.module,
            title=plan.title,
            goal=request.goal,
            eta_days=plan.eta_days,
            confidence=plan.confidence,
            current_stage_id=plan.stages[0].stage_id if plan.stages else None,
            stages_json=[s.model_dump() for s in plan.stages],
            adjustment_rationale=plan.adjustment_rationale,
            strategy_report=plan.strategy_report,
            search_evidence=_format_search_evidence(search_evidence),
            status="active"
        )
        self.session.add(db_path)
        await self.session.flush()

        db_nodes = []
        for agent_node in plan.nodes:
            db_node = CoursePathNode(
                path_id=db_path.id,
                user_id=user_id,
                node_id=agent_node.node_id,
                stage_id=agent_node.stage_id,
                title=agent_node.title,
                prerequisites=agent_node.prerequisites,
                mastery_target=agent_node.mastery_target,
                estimated_minutes=agent_node.estimated_minutes,
                difficulty=agent_node.difficulty,
                recommendation_reason=agent_node.recommendation_reason,
                priority=agent_node.priority,
                resource_policy=agent_node.resource_policy.model_dump() if agent_node.resource_policy else None,
                status="locked",
                resource_status="not_started",
            )

            if not agent_node.prerequisites:
                db_node.status = "available"
                if db_path.current_node_id is None:
                    db_path.current_node_id = agent_node.node_id
                    db_path.current_stage_id = agent_node.stage_id

            db_nodes.append(db_node)
            self.session.add(db_node)

        if commit:
            await self.session.commit()
            await self.session.refresh(db_path)
        else:
            await self.session.flush()
        return db_path, db_nodes

    async def generate_node_resources(
        self,
        *,
        user_id: int,
        node_id: int,
        selected_agents: list[AgentSelection],
        agent_configs: AgentConfigs,
        output_options: OutputOptions,
    ) -> dict[str, Any]:
        """为路径节点生成学习资源。

        校验流程：
        1. 节点必须存在且属于当前用户
        2. 节点必须为可学习状态，locked 不允许
        3. 如果已有 generating/ready 资源，返回已有 resource_id
        4. 从节点内容构造 learning_need
        5. 调用统一 start_resource_task
        """
        from app.resource.service import ResourceUsecases

        # 1 & 2: 验证节点存在且属于当前用户
        node_stmt = (
            select(CoursePathNode)
            .where(CoursePathNode.id == node_id, CoursePathNode.user_id == user_id)
            .with_for_update()
        )
        node = (await self.session.exec(node_stmt)).first()
        if node is None:
            raise ValueError("节点不存在或不属于当前用户")

        if node.status == "locked":
            raise ValueError("锁定节点不能生成资源")

        # 3: 检查已有资源绑定
        binding_stmt = select(CoursePathResourceBinding).where(
            CoursePathResourceBinding.node_id == node_id,
            CoursePathResourceBinding.user_id == user_id,
        ).order_by(col(CoursePathResourceBinding.created_at).desc())
        existing_binding = (await self.session.exec(binding_stmt)).first()

        if existing_binding and node.resource_status in ("generating", "ready"):
            return {
                "resource_id": existing_binding.resource_id,
                "node_id": node_id,
                "status": node.resource_status,
                "should_schedule": False,
            }

        # 4: 从节点内容构造 learning_need
        path_stmt = select(CoursePath).where(CoursePath.id == node.path_id)
        path = (await self.session.exec(path_stmt)).first()
        learning_need = self._build_node_learning_need(node, path)

        # Determine selected_agents: frontend choice > node policy > fallback
        if not selected_agents:
            policy = node.resource_policy
            if policy and policy.get("required_resource_types"):
                raw_types = policy["required_resource_types"]
            else:
                raw_types = get_resource_policy_fallback(node.difficulty)
        else:
            raw_types = [s.agent_id for s in selected_agents]

        # Filter unimplemented types, always produce at least one valid agent
        from app.path.schemas import ALLOWED_RESOURCE_TYPES
        resolved_types = [t for t in raw_types if t in ALLOWED_RESOURCE_TYPES]
        removed = set(raw_types) - set(resolved_types)
        if removed:
            logger.warning("过滤掉未实现的资源类型 %s for node %s", removed, node.node_id)
        if not resolved_types:
            resolved_types = ["content"]

        selected_agents = [AgentSelection(agent_id=t) for t in resolved_types]

        # 5: 构造 ResourceGenerationRequest
        request = ResourceGenerationRequest(
            learning_need=learning_need,
            learning_scenario="path_learning",
            selected_agents=selected_agents,
            agent_configs=agent_configs,
            output_options=output_options,
        )

        # Use unified start_resource_task
        usecases = ResourceUsecases(self.session)
        result = await usecases.start_resource_task(
            user_id=user_id,
            request=request,
            source="path_node",
            node_id=node_id,
        )

        # Read profile for background task dispatch
        memory_service = MemoryService(module="mentor")
        profile_record = await memory_service.get_profile(user_id=user_id)
        profile_dict = profile_record.model_dump(exclude_none=True) if profile_record else {}

        return {
            "resource_id": result["resource_id"],
            "node_id": node_id,
            "status": "generating",
            "should_schedule": True,
            "request": request,
            "profile": profile_dict,
            "actual_agents": resolved_types,
        }

    async def start_node(self, *, user_id: int, node_id: int) -> CoursePathResponse:
        """Start a ready learning node and make the active position explicit."""
        node = await self._get_owned_node_for_update(user_id=user_id, node_id=node_id)
        if node.status == "locked":
            raise ValueError("前置节点尚未完成，不能开始学习")
        if node.status == "completed":
            return await self._response_for_node_path(node)
        if node.resource_status != "ready":
            raise ValueError("学习资源尚未生成完成")

        node.status = "in_progress"
        node.started_at = node.started_at or datetime.now(timezone.utc)
        path = await self._get_path_for_update(node.path_id)
        path.current_node_id = node.node_id
        path.current_stage_id = node.stage_id
        await self.session.commit()
        return await self._response_for_path(path)

    async def complete_node(self, *, user_id: int, node_id: int) -> CoursePathResponse:
        """Complete a learning node and unlock successors whose dependencies are done."""
        node = await self._get_owned_node_for_update(user_id=user_id, node_id=node_id)
        path = await self._get_path_for_update(node.path_id)
        nodes = list(await self._get_nodes_for_path(path.id))

        if node.status == "locked":
            raise ValueError("前置节点尚未完成，不能标记完成")
        if node.status not in ("in_progress", "completed"):
            raise ValueError("请先开始学习该节点")

        if node.status != "completed":
            node.status = "completed"
            node.progress = 100
            node.completed_at = datetime.now(timezone.utc)

        completed_ids = {item.node_id for item in nodes if item.status == "completed"}
        completed_ids.add(node.node_id)
        for item in nodes:
            if item.status == "locked" and set(item.prerequisites or []).issubset(completed_ids):
                item.status = "available"

        completed_count = sum(1 for item in nodes if item.status == "completed")
        path.overall_progress = round(completed_count * 100 / len(nodes)) if nodes else 0
        next_node = next(
            (item for item in nodes if item.status == "in_progress"),
            next((item for item in nodes if item.status == "available"), None),
        )
        if completed_count == len(nodes) and nodes:
            path.overall_progress = 100
            path.current_node_id = None
            path.current_stage_id = None
        elif next_node:
            path.current_node_id = next_node.node_id
            path.current_stage_id = next_node.stage_id

        await self.session.commit()
        resource_map = await self._get_node_resource_ids([item.id for item in nodes if item.id is not None])
        return await self._build_path_response_async(path, nodes, resource_map)

    async def _build_resource_context(self, *, user_id: int, resource_id: int) -> str:
        """Summarize a generated resource for replanning without sending full content."""
        from app.infra.models import GeneratedResource, GeneratedResourceItem

        resource_stmt = select(GeneratedResource).where(
            GeneratedResource.id == resource_id,
            GeneratedResource.user_id == user_id,
        )
        resource = (await self.session.exec(resource_stmt)).first()
        if resource is None:
            return f"资源 {resource_id} 不存在或不属于当前用户"

        item_stmt = (
            select(GeneratedResourceItem)
            .where(
                GeneratedResourceItem.resource_id == resource_id,
                GeneratedResourceItem.user_id == user_id,
            )
            .order_by(GeneratedResourceItem.created_at)
        )
        items = (await self.session.exec(item_stmt)).all()

        parts = [f"资源 {resource_id} 学习需求：{resource.learning_need or '未记录'}"]
        for item in items[:6]:
            summary_parts = [
                f"- {item.agent_type}",
                f"标题：{item.title}" if item.title else "",
                f"摘要：{item.summary}" if item.summary else "",
                f"覆盖知识点：{', '.join(item.covered_knowledge_points or [])}" if item.covered_knowledge_points else "",
                f"覆盖薄弱点：{', '.join(item.weak_points_covered or [])}" if item.weak_points_covered else "",
            ]
            parts.append("；".join(part for part in summary_parts if part))
        return "\n".join(parts)[:4000]

    def _build_node_learning_need(self, node: CoursePathNode, path: CoursePath | None) -> str:
        """从节点和路径信息组装 learning_need 文本。"""
        parts = [f"当前学习节点：{node.title}"]
        if path:
            parts.append(f"路径标题：{path.title}")
            parts.append(f"路径目标：{path.goal}")
            parts.append(f"所属模块：{path.module}")
            stage = next(
                (
                    item for item in (path.stages_json or [])
                    if isinstance(item, dict) and item.get("stage_id") == node.stage_id
                ),
                None,
            )
            if stage:
                parts.append(f"当前阶段：{stage.get('title', node.stage_id)}")
                if stage.get("description"):
                    parts.append(f"阶段说明：{stage['description']}")
            else:
                parts.append(f"当前阶段：{node.stage_id}")
        if node.mastery_target:
            parts.append(f"学习目标：{node.mastery_target}")
        if node.prerequisites:
            parts.append(f"前置知识：{', '.join(node.prerequisites)}")
        if node.difficulty:
            parts.append(f"节点难度：{node.difficulty}")
        if node.estimated_minutes:
            parts.append(f"建议学习时长：{node.estimated_minutes} 分钟")
        parts.append(f"节点优先级：{node.priority}")
        if node.recommendation_reason:
            parts.append(f"推荐依据：{node.recommendation_reason}")
        if node.resource_policy:
            generation_focus = node.resource_policy.get("generation_focus", [])
            if generation_focus:
                parts.append(f"资源生成重点：{', '.join(generation_focus)}")
            personalization_reason = node.resource_policy.get("personalization_reason", "")
            if personalization_reason:
                parts.append(f"个性化原因：{personalization_reason}")
        parts.append("学习场景：路径学习中的当前节点学习资料生成")
        return "\n".join(parts)

    async def get_active_path(self, user_id: int, module: str = "mentor") -> CoursePathResponse | None:
        """获取用户当前正在进行的活跃课程路径。"""
        statement = select(CoursePath).where(
            CoursePath.user_id == user_id,
            CoursePath.module == module,
            CoursePath.status == "active"
        ).order_by(CoursePath.created_at.desc())

        result = await self.session.exec(statement)
        db_path = result.first()

        if not db_path:
            return None

        nodes = await self._get_nodes_for_path(db_path.id)
        node_ids = [n.id for n in nodes if n.id is not None]
        resource_map = await self._get_node_resource_ids(node_ids)

        return await self._build_path_response_async(db_path, nodes, resource_map)

    async def _get_owned_node_for_update(self, *, user_id: int, node_id: int) -> CoursePathNode:
        statement = (
            select(CoursePathNode)
            .where(CoursePathNode.id == node_id, CoursePathNode.user_id == user_id)
            .with_for_update()
        )
        node = (await self.session.exec(statement)).first()
        if node is None:
            raise ValueError("节点不存在或不属于当前用户")
        return node

    async def _get_path_for_update(self, path_id: int) -> CoursePath:
        statement = select(CoursePath).where(CoursePath.id == path_id).with_for_update()
        path = (await self.session.exec(statement)).first()
        if path is None:
            raise ValueError("学习路径不存在")
        return path

    async def _response_for_node_path(self, node: CoursePathNode) -> CoursePathResponse:
        path = await self._get_path_for_update(node.path_id)
        return await self._response_for_path(path)

    async def _response_for_path(self, path: CoursePath) -> CoursePathResponse:
        nodes = await self._get_nodes_for_path(path.id)
        resource_map = await self._get_node_resource_ids([node.id for node in nodes if node.id is not None])
        return await self._build_path_response_async(path, nodes, resource_map)

    async def _archive_active_paths(self, user_id: int, module: str) -> None:
        """将用户已有的活跃路径状态设为 archived。"""
        statement = select(CoursePath).where(
            CoursePath.user_id == user_id,
            CoursePath.module == module,
            CoursePath.status == "active"
        )
        result = await self.session.exec(statement)
        for path in result.all():
            path.status = "archived"
        await self.session.flush()

    async def _get_nodes_for_path(self, path_id: int) -> Sequence[CoursePathNode]:
        """获取指定路径的所有节点。"""
        statement = select(CoursePathNode).where(
            CoursePathNode.path_id == path_id
        ).order_by(CoursePathNode.id)
        result = await self.session.exec(statement)
        return result.all()

    async def _get_node_resource_ids(self, node_ids: list[int]) -> dict[int, int | None]:
        """查询节点与资源的绑定关系。"""
        if not node_ids:
            return {}

        stmt = select(CoursePathResourceBinding).where(
            col(CoursePathResourceBinding.node_id).in_(node_ids),
        ).order_by(col(CoursePathResourceBinding.created_at).desc())
        result = await self.session.exec(stmt)
        bindings = result.all()

        resource_map: dict[int, int | None] = {}
        for binding in bindings:
            resource_map.setdefault(binding.node_id, binding.resource_id)
        return resource_map

    async def _check_optimization_needs(
        self,
        user_id: int,
        path: CoursePath,
        nodes: Sequence[CoursePathNode],
    ) -> tuple[bool, list[str]]:
        """分析最近的学习事件，检测是否存在掌握程度不佳或对当前路径反馈不佳的诊断信号。"""
        from app.infra.models import LearningEvent

        # 查找该路径创建以来的学习事件
        stmt = (
            select(LearningEvent)
            .where(
                LearningEvent.user_id == user_id,
                LearningEvent.created_at >= path.created_at,
            )
            .order_by(LearningEvent.created_at.desc())
            .limit(50)
        )
        result = await self.session.exec(stmt)
        events = list(result.all())

        needs_opt = False
        tips = []

        # 1. 检查测验成绩不及格 (score < 65)
        low_score_events = [e for e in events if e.event_type == "quiz_submitted" and e.score is not None and e.score < 65]
        if low_score_events:
            needs_opt = True
            for e in low_score_events[:2]:
                topic_str = e.topic or e.course or "相关知识点"
                tips.append(f"检测到您在「{topic_str}」测验中得分偏低（{e.score:.0f}分），建议优化路径并添加巩固练习。")

        # 2. 检查用户负面反馈 (反馈含 难/看不懂/不会 等关键字)
        negative_feedback_events = [
            e for e in events
            if e.event_type in ("path_feedback", "resource_feedback")
            and e.feedback
            and any(kw in e.feedback for kw in ("太难", "看不懂", "不会", "卡住", "薄弱", "偏难", "跟不上"))
        ]
        if negative_feedback_events:
            needs_opt = True
            for e in negative_feedback_events[:2]:
                topic_str = e.topic or "当前内容"
                tips.append(f"您在学习「{topic_str}」时反馈表示“{e.feedback}”，建议微调难度。")

        # 3. 检查是否有用户反馈提及想要更多实操/图解
        pref_feedback_events = [
            e for e in events
            if e.event_type in ("path_feedback", "resource_feedback")
            and e.feedback
            and any(kw in e.feedback for kw in ("喜欢", "希望", "更想", "图解", "案例", "代码", "视频"))
        ]
        if pref_feedback_events:
            for e in pref_feedback_events[:2]:
                tips.append(f"已识别您的学习偏好反馈：“{e.feedback}”，可点击优化更新教学重点。")

        # 去重
        seen = set()
        unique_tips = []
        for t in tips:
            if t not in seen:
                seen.add(t)
                unique_tips.append(t)

        return needs_opt, unique_tips

    async def _build_path_response_async(
        self,
        path: CoursePath,
        nodes: Sequence[CoursePathNode],
        resource_map: dict[int, int | None] | None = None,
    ) -> CoursePathResponse:
        """异步构建学习路径 DTO，同时注入诊断反馈。"""
        needs_opt, tips = await self._check_optimization_needs(path.user_id, path, nodes)
        return self._build_path_response(path, nodes, resource_map, needs_optimization=needs_opt, optimization_tips=tips)

    def _build_path_response(
        self,
        path: CoursePath,
        nodes: Sequence[CoursePathNode],
        resource_map: dict[int, int | None] | None = None,
        needs_optimization: bool = False,
        optimization_tips: list[str] | None = None,
    ) -> CoursePathResponse:
        """将 ORM 模型转换为 API DTO。"""
        if resource_map is None:
            resource_map = {}

        node_dtos = [
            CoursePathNodeDTO(
                id=n.id,
                node_id=n.node_id,
                stage_id=n.stage_id,
                title=n.title,
                status=n.status,
                resource_status=n.resource_status,
                progress=n.progress,
                priority=n.priority,
                prerequisites=n.prerequisites or [],
                mastery_target=n.mastery_target,
                estimated_minutes=n.estimated_minutes,
                difficulty=n.difficulty,
                recommendation_reason=n.recommendation_reason,
                resource_id=resource_map.get(n.id, None) if n.id else None,
                resource_policy=n.resource_policy,
                recommended_agents=n.resource_policy.get("required_resource_types", []) if n.resource_policy else [],
                resource_generation_reason=n.resource_policy.get("personalization_reason", "") if n.resource_policy else None,
            )
            for n in nodes
        ]

        return CoursePathResponse(
            id=path.id,
            module=path.module,
            title=path.title,
            goal=path.goal,
            overall_progress=path.overall_progress,
            current_stage_id=path.current_stage_id,
            current_node_id=path.current_node_id,
            eta_days=path.eta_days,
            confidence=path.confidence,
            status=path.status,
            strategy_report=getattr(path, "strategy_report", None),
            stages=getattr(path, "stages_json", None) or [],
            nodes=node_dtos,
            needs_optimization=needs_optimization,
            optimization_tips=optimization_tips or [],
            search_evidence=getattr(path, "search_evidence", None) or [],
            created_at=path.created_at.isoformat() if path.created_at else ""
        )

    def _build_task_response(self, task: CoursePathGenerationTask) -> PathGenerationTaskResponse:
        return PathGenerationTaskResponse(
            task_id=int(task.id or 0),
            module=task.module,
            goal=task.goal,
            status=task.status,
            progress=task.progress,
            latest_message=task.latest_message,
            error_message=task.error_message,
            generated_path_id=task.generated_path_id,
        )


async def bg_generate_path_task(task_id: int) -> None:
    """使用独立会话执行慢速路径规划，API 请求无需等待模型完成。"""
    from app.infra.database import session_scope

    async with session_scope() as session:
        await CoursePathService(session).execute_generation_task(task_id)
