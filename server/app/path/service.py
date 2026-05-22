from typing import Sequence
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException
from loguru import logger

from app.memory.service import MemoryService
from app.infra.models import CoursePath, CoursePathNode
from app.path.agents.planner import PathPlannerAgent
from app.path.schemas import (
    CoursePathNodeDTO,
    CoursePathResponse,
    GeneratePathRequest,
)


class CoursePathService:
    """课程路径业务服务层。
    负责协调 Agent 进行规划，并负责数据库的持久化。
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.memory_layer = MemoryService()
        self.agent = PathPlannerAgent()

    async def generate_path(self, user_id: int, request: GeneratePathRequest) -> CoursePathResponse:
        """根据用户画像和需求，生成新的课程学习路径，并保存到数据库。"""
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
            adjustment_rationale=plan.adjustment_rationale,
            status="active"
        )
        self.session.add(db_path)
        await self.session.flush()

        # 5. 持久化节点
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
                status="locked"
            )
            
            # 如果没有前置条件，默认设为 available
            if not agent_node.prerequisites:
                db_node.status = "available"
                
            db_nodes.append(db_node)
            self.session.add(db_node)
        
        await self.session.commit()
        await self.session.refresh(db_path)

        # 6. 返回规范的 DTO
        return self._build_path_response(db_path, db_nodes)

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
        return self._build_path_response(db_path, nodes)

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

    def _build_path_response(self, path: CoursePath, nodes: Sequence[CoursePathNode]) -> CoursePathResponse:
        """将 ORM 模型转换为 API DTO。"""
        node_dtos = [
            CoursePathNodeDTO(
                id=n.id,
                node_id=n.node_id,
                stage_id=n.stage_id,
                title=n.title,
                status=n.status,
                progress=n.progress,
                priority=n.priority,
                prerequisites=n.prerequisites or [],
                mastery_target=n.mastery_target,
                estimated_minutes=n.estimated_minutes,
                difficulty=n.difficulty,
                recommendation_reason=n.recommendation_reason
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
            nodes=node_dtos,
            created_at=path.created_at.isoformat() if path.created_at else ""
        )
