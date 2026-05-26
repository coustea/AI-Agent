from typing import Any, Sequence
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import BackgroundTasks

from app.infra.logging import get_logger
from app.memory.service import MemoryService
from app.infra.models import CoursePath, CoursePathNode, CoursePathResourceBinding
from app.path.agents.planner import PathPlannerAgent
from app.path.schemas import (
    CoursePathNodeDTO,
    CoursePathResponse,
    GeneratePathRequest,
)

logger = get_logger(__name__)


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

        # 1. 获取用户画像
        profile = await self.memory_layer.get_or_create_profile(user_id)
        profile_dict = profile.profile_json if profile and profile.profile_json else {}

        # 2. 调用规划智能体
        plan = await self.agent.generate_plan(request, profile_dict)

        # 3. 如果存在之前的活跃路径，先归档它
        await self._archive_active_paths(user_id, request.module)

        # 4. 持久化新路径到数据库
        db_path = CoursePath(
            user_id=user_id,
            module=request.module,
            title=plan.title,
            goal=request.goal,
            eta_days=plan.eta_days,
            confidence=plan.confidence,
            stages_json=[s.model_dump() for s in plan.stages],
            adjustment_rationale=plan.adjustment_rationale,
            status="active"
        )
        self.session.add(db_path)
        await self.session.flush()

        # 5. 持久化节点 — resource_status 初始为 not_started
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
                status="locked",
                resource_status="not_started",
            )

            if not agent_node.prerequisites:
                db_node.status = "available"

            db_nodes.append(db_node)
            self.session.add(db_node)

        await self.session.commit()
        await self.session.refresh(db_path)

        return self._build_path_response(db_path, db_nodes)

    async def generate_node_resources(
        self,
        *,
        user_id: int,
        node_id: int,
        selected_agents: list,
        agent_configs: Any,
        output_options: Any,
    ) -> dict[str, Any]:
        """为路径节点生成学习资源。

        校验流程：
        1. 节点必须存在且属于当前用户
        2. 节点必须为可学习状态，locked 不允许
        3. 如果已有 generating/ready 资源，返回已有 resource_id
        4. 从节点内容构造 learning_need
        5. 调用统一 start_resource_task
        """
        from app.resource.schemas import AgentSelection, AgentConfigs, OutputOptions, ResourceGenerationRequest
        from app.resource.service import ResourceUsecases

        # 1 & 2: 验证节点存在且属于当前用户
        node = await self.session.get(CoursePathNode, node_id)
        if node is None or node.user_id != user_id:
            raise ValueError("节点不存在或不属于当前用户")

        if node.status == "locked":
            raise ValueError("锁定节点不能生成资源")

        # 3: 检查已有资源绑定
        binding_stmt = select(CoursePathResourceBinding).where(
            CoursePathResourceBinding.node_id == node_id,
            CoursePathResourceBinding.user_id == user_id,
        )
        existing_binding = (await self.session.exec(binding_stmt)).first()

        if existing_binding and node.resource_status in ("generating", "ready"):
            return {
                "resource_id": existing_binding.resource_id,
                "node_id": node_id,
                "status": node.resource_status,
            }

        # 4: 从节点内容构造 learning_need
        path_stmt = select(CoursePath).where(CoursePath.id == node.path_id)
        path = (await self.session.exec(path_stmt)).first()
        learning_need = self._build_node_learning_need(node, path)

        # 5: 构造 ResourceGenerationRequest
        request = ResourceGenerationRequest(
            learning_need=learning_need,
            learning_scenario="self_study",
            selected_agents=selected_agents,
            agent_configs=agent_configs if agent_configs else AgentConfigs(),
            output_options=output_options if output_options else OutputOptions(),
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
            "request": request,
            "profile": profile_dict,
        }

    def _build_node_learning_need(self, node: CoursePathNode, path: CoursePath | None) -> str:
        """从节点和路径信息组装 learning_need 文本。"""
        parts = [f"当前学习节点：{node.title}"]
        if path:
            parts.append(f"当前课程：{path.module}")
        if node.mastery_target:
            parts.append(f"学习目标：{node.mastery_target}")
        if node.prerequisites:
            parts.append(f"前置知识：{', '.join(node.prerequisites)}")
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

        return self._build_path_response(db_path, nodes, resource_map)

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
        )
        result = await self.session.exec(stmt)
        bindings = result.all()

        resource_map: dict[int, int | None] = {}
        for binding in bindings:
            resource_map[binding.node_id] = binding.resource_id
        return resource_map

    def _build_path_response(
        self,
        path: CoursePath,
        nodes: Sequence[CoursePathNode],
        resource_map: dict[int, int | None] | None = None,
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
            stages=path.stages_json or [],
            nodes=node_dtos,
            created_at=path.created_at.isoformat() if path.created_at else ""
        )