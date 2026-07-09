"""Resource-domain adapter for the shared cartoon animation capability.

Wraps CartoonVideoService into the resource-agent protocol so that
多智能体资源生成 and 路径规划节点资源生成
can produce animated explanation videos via the new CartoonAgent pipeline.

generate_resource: 多智能体资源流程，保存到 static/{username}/resources/{id}/cartoon/
generate_node: 路径规划节点流程，保存到 static/{username}/paths/{path_id}/nodes/{node_id}/cartoon/
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from app.config import (
    WORKPLACE_DIR,
    user_path_node_cartoon_dir,
    user_resource_cartoon_dir,
)
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.schemas import AgentResult, NodeInput, ResourceInput
from app.shared.cartoon.cartoon_agent import CartoonGenerationError
from app.shared.cartoon.service import CartoonVideoService

logger = get_logger(__name__)


@register_agent
class CartoonAgent(BaseResourceAgent):
    """Translate resource inputs into the cartoon animation pipeline."""

    agent_id = "cartoon"
    agent_name = "动画讲解"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self._service = CartoonVideoService()

    # -- Standalone resource entry point ------------------------------------

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        username = input_data.username
        resource_key = str(input_data.resource_id or uuid.uuid4().hex)
        output_dir = user_resource_cartoon_dir(username, resource_key)

        return await self._generate(
            learning_need=input_data.learning_need,
            profile=input_data.profile,
            output_dir=output_dir,
        )

    # -- Path node entry point ----------------------------------------------

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        username = input_data.username
        output_dir = user_path_node_cartoon_dir(
            username, str(input_data.path_id), str(input_data.node_id)
        )

        return await self._generate(
            learning_need=input_data.node_title,
            profile=input_data.profile,
            output_dir=output_dir,
        )

    # -- Shared generation logic --------------------------------------------

    async def _generate(
        self,
        *,
        learning_need: str,
        profile: dict[str, Any] | str | None,
        output_dir: Any,
    ) -> AgentResult:
        logger.info(
            "Agent[%s] 开始生成: learning_need=%s",
            self.agent_id,
            learning_need[:50],
        )
        started = time.perf_counter()

        task_id = uuid.uuid4().hex

        try:
            result = await self.run_with_heartbeat(
                self._service.generate(
                    task_id=task_id,
                    learning_need=learning_need,
                    profile=profile,
                ),
                messages=[
                    "正在生成动画分镜内容...",
                    "正在合成动画讲解视频...",
                ],
                interval_seconds=15.0,
                progress=75,
            )
        except CartoonGenerationError as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.error(
                "Agent[%s] 生成失败: error=%s elapsed_ms=%d",
                self.agent_id,
                exc,
                elapsed_ms,
            )
            return AgentResult(
                success=False,
                title=f"{learning_need} - 动画讲解视频",
                file_type="mp4",
                error=str(exc),
                metadata={
                    "agent_id": self.agent_id,
                    "problems": exc.audit.problems if exc.audit else [],
                },
            )
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.error(
                "Agent[%s] 生成异常: error=%s elapsed_ms=%d",
                self.agent_id,
                exc,
                elapsed_ms,
                exc_info=True,
            )
            return AgentResult(
                success=False,
                title=f"{learning_need} - 动画讲解视频",
                file_type="mp4",
                error=str(exc),
                metadata={"agent_id": self.agent_id},
            )

        # Compute relative paths from WORKPLACE_DIR for static serving
        video_path = result.video_path
        html_path = result.html_path
        video_url = f"/static/{video_path.relative_to(WORKPLACE_DIR)}" if video_path and video_path.exists() else ""
        html_url = f"/static/{html_path.relative_to(WORKPLACE_DIR)}" if html_path.exists() else ""

        content = json.dumps(
            {
                "schema_version": "cartoon/v2",
                "title": result.title,
                "video_url": video_url,
                "public_url": video_url,
                "html_url": html_url,
                "duration_seconds": result.duration,
                "scene_count": result.scene_count,
            },
            ensure_ascii=False,
        )

        video_size = video_path.stat().st_size if video_path and video_path.exists() else 0

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Agent[%s] 生成完成: scene_count=%d duration=%.1f video_size=%d elapsed_ms=%d",
            self.agent_id,
            result.scene_count,
            result.duration,
            video_size,
            elapsed_ms,
        )

        return AgentResult(
            success=True,
            content=content,
            file_type="mp4",
            title=f"{result.title} - 动画讲解视频",
            summary=(
                f"生成 {result.scene_count} 个场景、"
                f"{result.duration:.1f} 秒动画讲解视频"
            ),
            metrics={
                "scene_count": result.scene_count,
                "duration_seconds": round(result.duration, 2),
                "video_size_bytes": video_size,
            },
            metadata={
                "engine": "hyperframes",
                "agent_id": self.agent_id,
                "schema_version": "cartoon/v2",
                "delivery_mode": "mp4",
                "video_url": video_url,
                "html_url": html_url,
                "video_file_path": str(video_path) if video_path else "",
                "html_file_path": str(html_path),
                "title": result.title,
                "duration_seconds": result.duration,
                "scene_count": result.scene_count,
                "video_size_bytes": video_size,
            },
        )
