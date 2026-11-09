"""学习路径动画视频适配器。"""

from __future__ import annotations

from app.config import user_path_node_cartoon_dir
from app.path.schemas import PathResourceRequest
from app.resource.schemas import AgentResult
from app.shared.cartoon import (
    CartoonAgent,
    CartoonBrief,
    CartoonGenerationConfig,
    CartoonGenerationError,
)


class PathCartoonAdapter:
    """学习路径节点动画视频生成适配器。"""

    async def generate(self, request: PathResourceRequest) -> AgentResult:
        """根据路径节点与教程正文生成动画视频产物。"""
        tutorial = request.tutorial
        if tutorial is None or not tutorial.content_markdown.strip():
            return AgentResult(
                success=False,
                title="视频生成失败",
                file_type="mp4",
                error="缺少教程正文",
                metadata={"agent_id": "cartoon"},
            )

        granularity_depth = {"coarse": "focused", "standard": "standard", "fine": "deep"}
        granularity_density = {"coarse": "moderate", "standard": "rich", "fine": "intensive"}
        pace_map = {"slow": "calm", "normal": "balanced", "fast": "fast"}

        config = CartoonGenerationConfig(
            lesson_depth=granularity_depth.get(request.preferences.granularity, "standard"),  # type: ignore[arg-type]
            visual_density=granularity_density.get(request.preferences.granularity, "rich"),  # type: ignore[arg-type]
            pace=pace_map.get(request.preferences.pace, "balanced"),  # type: ignore[arg-type]
        )

        brief = CartoonBrief(
            title=request.node_title,
            learning_need=f"学习路径：{request.path_title} - 节点：{request.node_title}（目标：{request.path_goal}）",
            source_materials=[tutorial.content_markdown[:30000]],
            configuration=config,
        )

        target = user_path_node_cartoon_dir(
            request.username,
            str(request.path_id),
            str(request.node_id),
        )

        try:
            artifact = await CartoonAgent().generate(brief, target)
            return AgentResult(
                success=True,
                title=artifact.title,
                file_type="mp4",
                summary=f"生成 {artifact.scene_count} 个语义场景动画视频（时长 {artifact.duration_seconds:.1f} 秒）",
                metrics={
                    "scene_count": artifact.scene_count,
                    "duration_seconds": artifact.duration_seconds,
                },
                metadata=artifact.metadata(),
            )
        except CartoonGenerationError as exc:
            return AgentResult(
                success=False,
                title="视频生成失败",
                file_type="mp4",
                error=str(exc),
                metadata={"agent_id": "cartoon", "stage": exc.stage, "problems": exc.problems},
            )
        except Exception as exc:
            return AgentResult(
                success=False,
                title="视频生成失败",
                file_type="mp4",
                error=f"路径动画生成异常：{exc}",
                metadata={"agent_id": "cartoon"},
            )


__all__ = ["PathCartoonAdapter"]
