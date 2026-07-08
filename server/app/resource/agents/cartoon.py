"""Resource-domain adapter for the shared cartoon animation capability.

Wraps CartoonPipeline into the resource-agent protocol so that
多智能体资源生成 and 路径规划节点资源生成
can produce animated explanation videos with TTS narration.

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
from app.shared.cartoon.pipeline import CartoonPipeline
from app.shared.cartoon.renderer import CartoonVideoRenderer
from app.shared.cartoon.schemas import CartoonVideoRequest, SourceArtifact

logger = get_logger(__name__)


def _source_artifacts_from_handoffs(
    handoffs: dict[str, Any],
) -> list[SourceArtifact]:
    artifacts: list[SourceArtifact] = []
    for agent_id, ctx in handoffs.items():
        title = getattr(ctx, "title", None) or agent_id
        summary = getattr(ctx, "one_sentence_summary", None) or title
        materials: list[str] = []
        materials.extend(
            str(item).strip()[:2000]
            for item in getattr(ctx, "materials", [])[:8]
            if str(item).strip()
        )
        artifacts.append(
            SourceArtifact(
                agent_id=agent_id,
                title=title,
                summary=summary,
                materials=materials[:12],
            )
        )
    return artifacts


def _source_artifacts_from_results(
    results: dict[str, AgentResult],
) -> list[SourceArtifact]:
    return [
        SourceArtifact(
            agent_id=aid,
            title=r.title or aid,
            summary=r.summary or r.title or aid,
            materials=[r.content[:4000]] if r.content.strip() else [],
        )
        for aid, r in results.items()
        if r.success
    ]


def _split_text_to_materials(content: str, *, limit: int = 12000) -> list[str]:
    normalized = content.strip()[:limit]
    if not normalized:
        return []

    chunks: list[str] = []
    current = ""
    for paragraph in normalized.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        candidate = f"{current}\n\n{paragraph}".strip()
        if current and len(candidate) > 2400:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks[:12]


def _agent_config_defaults(config: dict[str, Any]) -> dict[str, Any]:
    """从 4 个核心参数构建 cartoon 请求选项。"""
    return {
        "style": config.get("style", "diagram"),
        "depth": config.get("depth", "standard"),
        "pace": config.get("pace", "normal"),
        "visuals": config.get("visuals", "balanced"),
    }


@register_agent
class CartoonAgent(BaseResourceAgent):
    """Translate resource inputs into the cartoon animation pipeline."""

    agent_id = "cartoon"
    agent_name = "动画讲解"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)

    # -- Standalone resource entry point ------------------------------------

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        cfg = _agent_config_defaults(input_data.agent_config)
        username = input_data.username
        resource_key = str(input_data.resource_id or uuid.uuid4().hex)
        output_dir = user_resource_cartoon_dir(username, resource_key)

        request = CartoonVideoRequest(
            learning_need=input_data.learning_need,
            profile=input_data.profile,
            teaching_plan=input_data.teaching_plan,
            style=cfg["style"],
            depth=cfg["depth"],
            pace=cfg["pace"],
            visuals=cfg["visuals"],
            output_dir=output_dir,
            artifacts=_source_artifacts_from_handoffs(input_data.upstream_handoffs),
        )

        return await self._generate(
            request,
            output_dir=output_dir,
        )

    # -- Path node entry point ----------------------------------------------

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        cfg = _agent_config_defaults(input_data.agent_config)
        username = input_data.username
        output_dir = user_path_node_cartoon_dir(username, str(input_data.path_id), str(input_data.node_id))

        artifacts: list[SourceArtifact] = []
        if input_data.tutorial_markdown:
            materials = _split_text_to_materials(input_data.tutorial_markdown)
            artifacts.append(
                SourceArtifact(
                    agent_id="tutorial",
                    title=input_data.tutorial_title or input_data.node_title,
                    summary=input_data.tutorial_summary or input_data.node_title,
                    materials=materials,
                )
            )

        artifacts.extend(_source_artifacts_from_results(input_data.existing_resources))

        request = CartoonVideoRequest(
            learning_need=input_data.node_title,
            profile=input_data.profile,
            style=cfg["style"],
            depth=cfg["depth"],
            pace=cfg["pace"],
            visuals=cfg["visuals"],
            output_dir=output_dir,
            artifacts=artifacts,
        )

        return await self._generate(
            request,
            output_dir=output_dir,
        )

    # -- Shared generation logic --------------------------------------------

    async def _generate(
        self,
        request: CartoonVideoRequest,
        *,
        output_dir: Any,
    ) -> AgentResult:
        logger.info(
            "Agent[%s] 开始生成: learning_need=%s style=%s depth=%s pace=%s",
            self.agent_id, request.learning_need[:50],
            request.style, request.depth, request.pace,
        )
        started = time.perf_counter()

        pipeline = CartoonPipeline(renderer=CartoonVideoRenderer())

        async def progress(message: str, percent: int) -> None:
            await self.emitter.send(self.agent_id, "running", message, percent)

        try:
            artifact = await self.run_with_heartbeat(
                pipeline.generate(request, progress=progress),
                messages=[
                    "正在生成动画分镜内容...",
                    "正在合成配音与字幕...",
                    "正在渲染动画讲解视频...",
                ],
                interval_seconds=15.0,
                progress=75,
            )
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.error(
                "Agent[%s] 生成失败: error=%s elapsed_ms=%d",
                self.agent_id, exc, elapsed_ms, exc_info=True,
            )
            return AgentResult(
                success=False,
                title=f"{request.learning_need} - 动画讲解视频",
                file_type="mp4",
                error=str(exc),
                metadata={"agent_id": self.agent_id},
            )

        # Compute relative path from WORKPLACE_DIR for static serving
        video_rel = artifact.video_path.relative_to(WORKPLACE_DIR)
        html_rel = (output_dir / "index.html").relative_to(WORKPLACE_DIR)
        video_url = f"/static/{video_rel}"
        html_url = f"/static/{html_rel}"

        content = json.dumps(
            {
                "schema_version": "cartoon/v1",
                "title": artifact.brief.title,
                "video_url": video_url,
                "public_url": video_url,
                "html_url": html_url,
                "duration_seconds": artifact.brief.total_duration,
                "scene_count": artifact.scene_count,
                "style": artifact.theme,
            },
            ensure_ascii=False,
        )

        video_size = (
            artifact.video_path.stat().st_size
            if artifact.video_path.exists()
            else 0
        )

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Agent[%s] 生成完成: scene_count=%d duration=%.1f video_size=%d elapsed_ms=%d",
            self.agent_id, artifact.scene_count,
            artifact.brief.total_duration, video_size, elapsed_ms,
        )

        return AgentResult(
            success=True,
            content=content,
            file_type="mp4",
            title=f"{artifact.brief.title} - 动画讲解视频",
            summary=(
                f"生成 {artifact.scene_count} 个场景、"
                f"{artifact.brief.total_duration:.1f} 秒动画讲解视频"
            ),
            metrics={
                "scene_count": artifact.scene_count,
                "duration_seconds": round(artifact.brief.total_duration, 2),
                "video_size_bytes": video_size,
            },
            metadata={
                "engine": "hyperframes",
                "agent_id": self.agent_id,
                "schema_version": "cartoon/v1",
                "delivery_mode": "mp4",
                "video_url": video_url,
                "html_url": html_url,
                "video_file_path": str(artifact.video_path),
                "html_file_path": str(output_dir / "index.html"),
                "title": artifact.brief.title,
                "duration_seconds": artifact.brief.total_duration,
                "scene_count": artifact.scene_count,
                "style": artifact.theme,
                "video_size_bytes": video_size,
                "has_audio": True,
                "render_profile": artifact.render_profile.as_metadata(),
            },
        )
