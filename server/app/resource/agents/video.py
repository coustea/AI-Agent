"""Resource-domain adapter for the shared teaching-video capability."""

from __future__ import annotations

import json
import uuid
from typing import Any

from app.config import user_resource_video_dir, user_path_node_video_dir
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.schemas import AgentResult, NodeInput, ResourceInput
from app.shared.video.agent import VideoAgent as SharedVideoAgent
from app.shared.video.schemas import SourceMaterial, VideoRequest

logger = get_logger(__name__)


def _profile_text(profile: str | dict[str, Any]) -> str:
    if isinstance(profile, str):
        return profile.strip()
    return json.dumps(profile, ensure_ascii=False) if profile else ""


def _resource_materials(input_data: ResourceInput) -> list[SourceMaterial]:
    materials = [
        SourceMaterial(
            source_id=agent_id,
            source_type="resource_handoff",
            title=context.title,
            content=context.model_dump_json(),
            metadata={"source_agent": context.source_agent},
        )
        for agent_id, context in input_data.upstream_handoffs.items()
    ]
    if input_data.teaching_plan is not None:
        materials.append(
            SourceMaterial(
                source_id="teaching_plan",
                source_type="teaching_plan",
                title=input_data.learning_need,
                content=input_data.teaching_plan.model_dump_json(),
            )
        )
    if not materials:
        materials.append(
            SourceMaterial(
                source_id="learning_need",
                source_type="user_request",
                title=input_data.learning_need,
                content=input_data.learning_need,
            )
        )
    return materials


def _node_materials(input_data: NodeInput) -> list[SourceMaterial]:
    materials = [
        SourceMaterial(
            source_id="tutorial",
            source_type="path_tutorial",
            title=input_data.tutorial_title,
            content=input_data.tutorial_markdown,
            metadata={
                "path_id": input_data.path_id,
                "node_id": input_data.node_id,
                "knowledge_points": input_data.knowledge_points,
            },
        )
    ]
    for agent_id, result in input_data.existing_resources.items():
        if result.success and result.content:
            materials.append(
                SourceMaterial(
                    source_id=f"resource:{agent_id}",
                    source_type="generated_resource",
                    title=result.title or agent_id,
                    content=result.content,
                    metadata={"source_agent": agent_id},
                )
            )
    return materials


def _request_options(config: dict[str, Any]) -> dict[str, Any]:
    """从 4 个核心参数构建 VideoRequest 选项。

    scene_count 由 duration_seconds 自动计算（约30秒/场景），
    不再由用户直接配置。
    """
    duration = int(config.get("duration_seconds", 180))
    return {
        "duration_seconds": duration,
        "scene_count": max(3, min(12, round(duration / 30))),
        "aspect_ratio": config.get("aspect_ratio", "16:9"),
        "voice": config.get("voice", "teacher"),
        "include_captions": bool(config.get("include_captions", True)),
    }


@register_agent
class VideoAgent(BaseResourceAgent):
    """Translate resource inputs into the shared source-neutral video contract."""

    agent_id = "video"
    agent_name = "讲解视频"

    def __init__(self, emitter=None, *, video_agent: SharedVideoAgent | None = None):
        super().__init__(emitter=emitter)
        self.video_agent = video_agent or SharedVideoAgent()

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        username = input_data.username or "anonymous"
        output_dir = user_resource_video_dir(username, str(input_data.resource_id or uuid.uuid4().hex))
        request = VideoRequest(
            topic=input_data.learning_need,
            audience=_profile_text(input_data.profile),
            learning_goal=input_data.learning_need,
            materials=_resource_materials(input_data),
            output_dir=output_dir,
            metadata={
                "origin": "resource",
                "resource_id": input_data.resource_id,
                "learning_scenario": input_data.learning_scenario,
            },
            **_request_options(input_data.agent_config),
        )
        return await self._generate(request)

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        username = input_data.username or "anonymous"
        request = VideoRequest(
            topic=input_data.node_title,
            audience=_profile_text(input_data.profile),
            learning_goal=input_data.mastery_target or input_data.path_goal,
            materials=_node_materials(input_data),
            output_dir=user_path_node_video_dir(username, str(input_data.path_id), str(input_data.node_id)),
            metadata={
                "origin": "path",
                "path_id": input_data.path_id,
                "node_id": input_data.node_id,
                "node_key": input_data.node_key,
            },
            **_request_options(input_data.agent_config),
        )
        return await self._generate(request)

    async def _generate(self, request: VideoRequest) -> AgentResult:
        await self.emitter.send(
            self.agent_id,
            "running",
            "正在规划讲解节奏、生成配音并渲染视频...",
            15,
        )
        try:
            artifact = await self.video_agent.generate(request)
        except Exception as exc:
            logger.error("VideoAgent generation failed: %s", exc, exc_info=True)
            await self.emitter.send(
                self.agent_id,
                "failed",
                f"讲解视频生成失败: {exc}",
                0,
            )
            return AgentResult(
                success=False,
                title=f"{request.topic} - 视频",
                summary="讲解视频生成失败",
                error=str(exc),
                metadata={
                    "agent_id": self.agent_id,
                    "schema_version": "video/v2",
                },
            )

        content = json.dumps(
            {
                "schema_version": artifact.plan.schema_version,
                "title": artifact.plan.title,
                "public_url": artifact.public_url,
                "duration_ms": artifact.duration_ms,
                "width": artifact.width,
                "height": artifact.height,
                "size_bytes": artifact.size_bytes,
                "style": artifact.plan.style.id,
            },
            ensure_ascii=False,
        )
        await self.emitter.send(
            self.agent_id,
            "completed",
            "讲解视频已完成",
            100,
        )
        return AgentResult(
            success=True,
            content=content,
            file_type="mp4",
            title=artifact.plan.title,
            summary=f"生成 {len(artifact.plan.scenes)} 个场景的讲解视频",
            metrics={
                "scene_count": len(artifact.plan.scenes),
                "duration_seconds": round(artifact.duration_ms / 1000, 2),
            },
            metadata={
                "engine": "remotion",
                "agent_id": self.agent_id,
                "schema_version": artifact.plan.schema_version,
                "delivery_mode": "mp4",
                "public_url": artifact.public_url,
                "file_path": str(artifact.mp4_path),
                "title": artifact.plan.title,
                "duration_ms": artifact.duration_ms,
                "width": artifact.width,
                "height": artifact.height,
                "size_bytes": artifact.size_bytes,
                "style": artifact.plan.style.id,
                "aspect_ratio": artifact.plan.aspect_ratio,
                "has_audio": True,
                "has_captions": request.include_captions,
            },
        )
