"""资源生成 Agent — 动画讲解视频。

仅做注册和心跳包装，逻辑全在 CartoonService。
"""

from __future__ import annotations

from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.schemas import AgentResult, ResourceInput
from app.shared.cartoon import CartoonService

logger = get_logger(__name__)


@register_agent
class CartoonAgent(BaseResourceAgent):
    """动画讲解视频生成 Agent — 仅做注册和心跳包装。"""

    agent_id = "cartoon"
    agent_name = "动画讲解"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self._service = CartoonService()

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        """多智能体资源生成入口 — 委托给 CartoonService。"""
        logger.info("Agent[cartoon] 开始生成: learning_need=%s", input_data.learning_need[:50])

        return await self.run_with_heartbeat(
            self._service.generate_resource(input_data),
            messages=["正在生成动画分镜内容...", "正在合成动画讲解视频..."],
            interval_seconds=15.0,
            progress=75,
        )