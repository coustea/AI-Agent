"""Resource-domain adapter for the shared cartoon animation capability.

Wraps CartoonPipeline into the resource-agent protocol so that
standalone resource generation and path-node resource generation
can produce animated explanation videos with TTS narration.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from app.config import CARTOON_RENDER_WORKERS, WORKPLACE_DIR
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.schemas import AgentResult, NodeInput, ResourceInput
from app.shared.cartoon.pipeline import CartoonPipeline
from app.shared.cartoon.renderer import CartoonVideoRenderer
from app.shared.cartoon.schemas import CartoonVideoRequest, SourceArtifact

logger = get_logger(__name__)


def _profile_text(profile: str | dict[str, Any]) -> str | dict[str, Any]:
    return profile


def _source_artifacts_from_handoffs(
    handoffs: dict[str, Any],
) -> list[SourceArtifact]:
    artifacts: list[SourceArtifact] = []
    for agent_id, ctx in handoffs.items():
        title = getattr(ctx, "title", None) or agent_id
        summary = getattr(ctx, "one_sentence_summary", None) or title
        materials: list[str] = []
        reusable = getattr(ctx, "reusable_assets", None)
        if reusable:
            materials.extend(
                str(item)
                for item in getattr(reusable, "examples", [])[:4]
                if str(item).strip()
            )
            materials.extend(
                str(item)
                for item in getattr(reusable, "visual_ideas", [])[:4]
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


def _agent_config_defaults(config: dict[str, Any]) -> dict[str, Any]:
    """从 4 个核心参数构建 cartoon 请求选项。

    render_workers 从 config.yaml 读取，不再由用户配置。
    """
    return {
        "video_length_seconds": int(config.get("video_length_seconds", 90)),
        "voice": config.get("voice", "teacher"),
        "style": config.get("style", "diagram"),
        "focus": config.get("focus", "concept"),
    }


@register_agent
class CartoonAgent(BaseResourceAgent):
    """Translate resource inputs into the cartoon animation pipeline."""

    agent_id = "cartoon"
    agent_name = "动画讲解视频"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)

    # -- Standalone resource entry point ------------------------------------

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        cfg = _agent_config_defaults(input_data.agent_config)
        user_id = input_data.user_id or 0
        resource_key = str(input_data.resource_id or uuid.uuid4().hex)
        output_dir = WORKPLACE_DIR / "cartoon" / str(user_id) / resource_key

        request = CartoonVideoRequest(
            learning_need=input_data.learning_need,
            profile=_profile_text(input_data.profile),
            video_length_seconds=cfg["video_length_seconds"],
            voice=cfg["voice"],
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
        output_dir = (
            WORKPLACE_DIR
            / "cartoon"
            / f"path_{input_data.path_id}"
            / f"node_{input_data.node_id}"
        )

        request = CartoonVideoRequest(
            learning_need=input_data.learning_need,
            profile=_profile_text(input_data.profile),
            video_length_seconds=cfg["video_length_seconds"],
            voice=cfg["voice"],
            output_dir=output_dir,
            artifacts=_source_artifacts_from_results(input_data.existing_resources),
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
        renderer = CartoonVideoRenderer(timeout_seconds=600, workers=CARTOON_RENDER_WORKERS)
        pipeline = CartoonPipeline(renderer=renderer)

        async def progress(message: str, percent: int) -> None:
            await self.emitter.send(self.agent_id, "running", message, percent)

        try:
            artifact = await pipeline.generate(request, progress=progress)
        except Exception as exc:
            logger.error("CartoonAgent generation failed: %s", exc, exc_info=True)
            await self.emitter.send(
                self.agent_id,
                "failed",
                f"动画讲解视频生成失败: {exc}",
                0,
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
                "html_url": html_url,
                "duration_seconds": artifact.brief.total_duration,
                "scene_count": artifact.scene_count,
                "style": artifact.style.selected.name,
                "repaired": artifact.repaired,
            },
            ensure_ascii=False,
        )

        await self.emitter.send(
            self.agent_id,
            "completed",
            "动画讲解视频已完成",
            100,
        )

        video_size = (
            artifact.video_path.stat().st_size
            if artifact.video_path.exists()
            else 0
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
                "style": artifact.style.selected.name,
                "repaired": artifact.repaired,
                "video_size_bytes": video_size,
                "has_audio": True,
                "render_workers": CARTOON_RENDER_WORKERS,
            },
        )
