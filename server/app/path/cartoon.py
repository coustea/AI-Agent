"""Learning-path adapter for cartoon generation."""

from __future__ import annotations

import time
from typing import Any

from app.config import static_url, user_path_node_cartoon_dir
from app.infra.logging import get_logger
from app.path.schemas import PathResourceRequest
from app.resource.schemas import AgentResult
from app.shared.cartoon import (
    CartoonAgent,
    CartoonBrief,
    CartoonGenerationConfig,
    CartoonGenerationError,
    CartoonResourceMetadata,
)
from app.shared.cartoon.schemas import LessonDepth


logger = get_logger(__name__)


class PathCartoonAdapter:
    def __init__(self, *, pipeline: CartoonAgent | None = None) -> None:
        self._pipeline = pipeline or CartoonAgent()

    async def generate(self, request: PathResourceRequest) -> AgentResult:
        started = time.perf_counter()
        try:
            brief = self._brief(request)
            target = user_path_node_cartoon_dir(
                self._safe_username(request.username or request.user_id),
                str(request.path_id),
                str(request.node_id),
            )
            artifact = await self._pipeline.generate(brief, target)
            duration_seconds = round(artifact.duration_ms / 1_000, 2)
            logger.info(
                "[PathCartoon] 动画生成成功: node_id=%s scenes=%s duration=%.1fs",
                request.node_id, artifact.scene_count, duration_seconds,
            )
            metadata = CartoonResourceMetadata(
                video_url=static_url(artifact.video_path),
                preview_url=static_url(artifact.html_path),
                captions_url=static_url(artifact.caption_path),
                duration_seconds=duration_seconds,
                scene_count=artifact.scene_count,
            )
            return AgentResult(
                success=True,
                title=artifact.title,
                file_type="mp4",
                summary=f"{artifact.scene_count} 个语义场景，时长 {duration_seconds:.1f} 秒",
                metrics={
                    "scene_count": artifact.scene_count,
                    "duration_seconds": duration_seconds,
                    "elapsed_ms": round((time.perf_counter() - started) * 1_000),
                },
                metadata=metadata.model_dump(mode="json"),
            )
        except CartoonGenerationError as exc:
            logger.warning("[PathCartoon] 动画生成失败: node_id=%s stage=%s", request.node_id, exc.stage)
            return self._failure(request.node_title, exc, started)
        except Exception as exc:
            logger.exception("Path cartoon generation failed: node_id=%s", request.node_id)
            return self._failure(
                request.node_title,
                CartoonGenerationError(
                    f"路径动画生成异常: {exc}",
                    stage="path-adapter",
                    problems=[str(exc)],
                ),
                started,
            )

    @staticmethod
    def _brief(request: PathResourceRequest) -> CartoonBrief:
        tutorial = request.tutorial
        if tutorial is None or not tutorial.content_markdown.strip():
            raise CartoonGenerationError(
                "路径节点缺少教程正文，不能生成动画",
                stage="request",
            )
        return CartoonBrief(
            learning_need=request.node_title.strip()[:500],
            instruction_context={
                "entry": "path",
                "path_title": request.path_title,
                "path_goal": request.path_goal,
                "node_title": request.node_title,
                "difficulty": request.difficulty,
                "tutorial_title": tutorial.title,
                "tutorial_summary": tutorial.summary or "",
                "preferences": request.preferences.model_dump(mode="json"),
            },
            source_materials=[tutorial.content_markdown[:30_000]],
            knowledge_points=list(tutorial.knowledge_points)[:30],
            weak_knowledge_points=list(tutorial.weak_knowledge_points)[:20],
            configuration=CartoonGenerationConfig(
                lesson_depth={
                    "coarse": LessonDepth.FOCUSED,
                    "standard": LessonDepth.STANDARD,
                    "fine": LessonDepth.DEEP,
                }[request.preferences.granularity],
                visual_density={
                    "coarse": "moderate",
                    "standard": "rich",
                    "fine": "intensive",
                }[request.preferences.granularity],
                pace={
                    "slow": "calm",
                    "normal": "balanced",
                    "fast": "fast",
                }[request.preferences.pace],
            ),
        )

    @staticmethod
    def _safe_username(value: Any) -> str:
        safe = "".join(char for char in str(value or "anonymous") if char.isalnum() or char in "-_")
        return safe[:80] or "anonymous"

    @staticmethod
    def _failure(title: str, exc: CartoonGenerationError, started: float) -> AgentResult:
        return AgentResult(
            success=False,
            title=f"{title[:48]} - 动画讲解视频",
            file_type="mp4",
            error=str(exc),
            metrics={"elapsed_ms": round((time.perf_counter() - started) * 1_000)},
            metadata={
                "agent_id": "cartoon",
                "stage": exc.stage,
                "problems": exc.problems,
            },
        )
