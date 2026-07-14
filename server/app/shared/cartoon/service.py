"""Business adapter for cartoon video generation.

Public surface:
- generate_resource(ResourceInput) -> AgentResult
- generate_for_path(PathResourceRequest) -> AgentResult
- generate_for_chat(...) -> ChatCartoonArtifact

The service only adapts business requests, owns isolated workspaces and atomic
publication, and converts the generated artifact into a small resource card.
All video-generation work is delegated to CartoonVideoAgent.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TYPE_CHECKING
from uuid import uuid4

from pydantic import (
    BaseModel,
    ValidationError,
)

from app.config import (
    static_url,
    user_chat_video_dir,
    user_path_node_cartoon_dir,
    user_resource_cartoon_dir,
)
from app.infra.logging import get_logger
from app.shared.cartoon.agent import (
    CartoonGenerationError,
    CartoonGenerationResult,
    CartoonVideoAgent,
)
from app.shared.cartoon.schemas import (
    CartoonBrief,
    CartoonGenerationConfig,
)

if TYPE_CHECKING:
    from app.path.schemas import (
        PathResourceRequest,
    )
    from app.resource.schemas import (
        AgentResult,
        ResourceInput,
    )

logger = get_logger(__name__)


@dataclass(frozen=True)
class ChatCartoonArtifact:
    """Small, frontend-safe result for an explicitly requested chat video."""

    title: str
    video_url: str
    preview_url: str
    duration_seconds: float
    scene_count: int


class CartoonService:
    """Expose business-specific entry points for cartoon generation."""

    def __init__(
        self,
        *,
        agent: CartoonVideoAgent | None = None,
    ) -> None:
        self._agent = (
            agent
            or CartoonVideoAgent()
        )

        self._locks: dict[
            str,
            asyncio.Lock,
        ] = {}

        self._locks_guard = asyncio.Lock()

    async def generate_resource(
        self,
        input_data: "ResourceInput",
    ) -> "AgentResult":
        """Generate a video for the multi-agent resource workflow."""
        started = time.perf_counter()

        learning_need = self._bounded_text(
            input_data.learning_need,
            500,
        )

        username = self._username(
            input_data.username,
            getattr(
                input_data,
                "user_id",
                None,
            ),
        )

        resource_key = (
            str(input_data.resource_id)
            if input_data.resource_id is not None
            else uuid4().hex
        )

        output_dir = user_resource_cartoon_dir(
            username,
            resource_key,
        )

        try:
            brief = self._build_resource_brief(
                input_data
            )

            artifact = await self._generate_and_publish(
                brief,
                output_dir,
            )

            return self._build_card_result(
                artifact,
                started,
            )

        except CartoonGenerationError as exc:
            return self._build_error_result(
                learning_need,
                exc,
                started,
            )

        except (
            ValidationError,
            ValueError,
        ) as exc:
            wrapped = CartoonGenerationError(
                f"动画视频请求参数无效: {exc}",
                stage="request",
                problems=[str(exc)],
            )

            return self._build_error_result(
                learning_need,
                wrapped,
                started,
            )

        except Exception as exc:
            logger.exception(
                "Cartoon resource generation failed"
            )

            wrapped = CartoonGenerationError(
                f"动画视频生成异常: {exc}",
                stage="service",
                problems=[str(exc)],
            )

            return self._build_error_result(
                learning_need,
                wrapped,
                started,
            )

    async def generate_for_path(
        self,
        request: "PathResourceRequest",
    ) -> "AgentResult":
        """Generate a video for one learning-path node."""
        logger.info(
            "[CartoonService] 开始动画视频生成: node_id=%s node_title=%s",
            request.node_id, request.node_title,
        )
        started = time.perf_counter()

        node_title = self._bounded_text(
            request.node_title,
            500,
        )

        username = self._username(
            request.username,
            getattr(
                request,
                "user_id",
                None,
            ),
        )

        output_dir = user_path_node_cartoon_dir(
            username,
            str(request.path_id),
            str(request.node_id),
        )
        logger.info("[CartoonService] 输出目录: %s", output_dir)

        try:
            logger.info("[CartoonService] 构建视频简报")
            brief = self._build_path_brief(
                request
            )
            logger.info(
                "[CartoonService] 调用 _generate_and_publish 开始生成",
            )

            artifact = await self._generate_and_publish(
                brief,
                output_dir,
            )

            logger.info(
                "[CartoonService] 动画视频生成成功: video_path=%s duration=%.2fs",
                artifact.video_path, time.perf_counter() - started,
            )

            return self._build_card_result(
                artifact,
                started,
            )

        except CartoonGenerationError as exc:
            logger.error(
                "[CartoonService] 动画视频生成失败: stage=%s error=%s",
                exc.stage, exc, exc_info=True,
            )
            return self._build_error_result(
                node_title,
                exc,
                started,
            )

        except (
            ValidationError,
            ValueError,
        ) as exc:
            logger.error(
                "[CartoonService] 动画视频请求参数无效: %s",
                exc, exc_info=True,
            )
            wrapped = CartoonGenerationError(
                f"动画视频请求参数无效: {exc}",
                stage="request",
                problems=[str(exc)],
            )

            return self._build_error_result(
                node_title,
                wrapped,
                started,
            )

        except Exception as exc:
            logger.exception(
                "[CartoonService] Cartoon path generation failed: node_id=%s error=%s",
                request.node_id, exc,
            )

            wrapped = CartoonGenerationError(
                f"动画视频生成异常: {exc}",
                stage="service",
                problems=[str(exc)],
            )

            return self._build_error_result(
                node_title,
                wrapped,
                started,
            )

    async def generate_for_chat(
        self,
        *,
        topic: str,
        username: str,
        session_id: str,
        message_id: int,
    ) -> ChatCartoonArtifact:
        """Generate a video requested directly by a chat user, never by the LLM."""
        normalized_topic = self._bounded_text(topic, 500)
        if not normalized_topic:
            raise ValueError("视频主题不能为空")

        artifact = await self._generate_and_publish(
            CartoonBrief(
                learning_need=normalized_topic,
                instruction_context={
                    "entry": "chat",
                    "teaching_goal": "从概念、机制、示例与总结四个层次组织讲解，并用动态模型呈现关键过程。",
                },
                source_materials=[normalized_topic],
                configuration=CartoonGenerationConfig(),
            ),
            user_chat_video_dir(username, session_id, message_id),
        )
        return ChatCartoonArtifact(
            title=artifact.title,
            video_url=static_url(artifact.video_path),
            preview_url=static_url(artifact.html_path),
            duration_seconds=round(artifact.duration_ms / 1000, 2),
            scene_count=artifact.scene_count,
        )

    def _build_resource_brief(
        self,
        input_data: "ResourceInput",
    ) -> CartoonBrief:
        raw_config = dict(
            input_data.agent_config
            or {}
        )

        configuration = (
            self._build_generation_config(
                raw_config
            )
        )

        if input_data.teaching_plan is None:
            raise ValueError("资源动画生成缺少结构化教学计划")

        plan = input_data.teaching_plan
        task = plan.task_for("cartoon")
        handoffs = self._normalize_mapping(input_data.upstream_handoffs or {})

        return CartoonBrief(
            learning_need=self._bounded_text(
                input_data.learning_need,
                500,
            ),
            instruction_context={
                "entry": "resource",
                "course_title": plan.title,
                "learner_goal": plan.learner_goal,
                "scope": plan.scope,
                "learning_thread": plan.learning_thread,
                "consistency_rules": plan.consistency_rules,
                "task": task.model_dump(mode="json"),
            },
            source_materials=self._source_materials(handoffs),
            knowledge_points=self._string_list(
                raw_config.get(
                    "knowledge_points"
                ),
                30,
            ),
            weak_knowledge_points=self._string_list(
                raw_config.get(
                    "weak_knowledge_points"
                ),
                20,
            ),
            configuration=configuration,
        )

    def _build_path_brief(
        self,
        request: "PathResourceRequest",
    ) -> CartoonBrief:
        tutorial = request.tutorial

        if tutorial is None:
            raise ValueError(
                "路径节点缺少教程内容，不能生成动画视频"
            )

        tutorial_markdown = self._bounded_text(
            tutorial.content_markdown,
            30000,
        )

        if not tutorial_markdown:
            raise ValueError(
                "路径节点教程正文为空，不能生成动画视频"
            )

        path_context = {
            "path_title": getattr(
                request,
                "path_title",
                "",
            ),
            "path_goal": getattr(
                request,
                "path_goal",
                "",
            ),
            "node_title": request.node_title,
            "difficulty": getattr(
                request,
                "difficulty",
                "",
            ),
            "mastery_target": getattr(
                request,
                "mastery_target",
                "",
            ),
            "generation_focus": list(
                getattr(
                    request,
                    "generation_focus",
                    [],
                )
                or []
            ),
            "tutorial_title": getattr(
                tutorial,
                "title",
                "",
            ),
            "tutorial_summary": getattr(
                tutorial,
                "summary",
                "",
            ),
        }

        raw_config = dict(
            getattr(
                request,
                "agent_config",
                {},
            )
            or {}
        )

        knowledge_points = list(
            getattr(
                tutorial,
                "knowledge_points",
                None,
            )
            or getattr(
                request,
                "knowledge_points",
                None,
            )
            or []
        )

        weak_points = list(
            getattr(
                tutorial,
                "weak_knowledge_points",
                None,
            )
            or getattr(
                request,
                "weak_knowledge_points",
                None,
            )
            or []
        )

        return CartoonBrief(
            learning_need=self._bounded_text(
                request.node_title,
                500,
            ),
            instruction_context={
                "entry": "path",
                **path_context,
            },
            source_materials=[tutorial_markdown],
            knowledge_points=self._string_list(
                knowledge_points,
                30,
            ),
            weak_knowledge_points=self._string_list(
                weak_points,
                20,
            ),
            configuration=self._build_generation_config(
                raw_config
            ),
        )

    async def _generate_and_publish(
        self,
        brief: CartoonBrief,
        output_dir: Path,
    ) -> CartoonGenerationResult:
        output_dir.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        workspace = (
            output_dir.parent
            / (
                f".{output_dir.name}."
                f"work-{uuid4().hex}"
            )
        )

        workspace.mkdir(
            parents=False,
            exist_ok=False,
        )

        logger.info(
            (
                "Cartoon generation start: "
                "target=%s workspace=%s need=%s"
            ),
            output_dir,
            workspace,
            brief.learning_need[:80],
        )

        try:
            artifact = await self._agent.generate(
                brief,
                workspace,
            )

            relative_paths = (
                self._artifact_relative_paths(
                    artifact,
                    workspace,
                )
            )

            await self._publish_workspace(
                workspace,
                output_dir,
            )

            published = self._rebase_artifact(
                artifact,
                output_dir,
                relative_paths,
            )

            logger.info(
                (
                    "Cartoon generation complete: "
                    "target=%s title=%s duration_ms=%d"
                ),
                output_dir,
                published.title,
                published.duration_ms,
            )

            return published

        except Exception:
            if workspace.exists():
                shutil.rmtree(
                    workspace,
                    ignore_errors=True,
                )

            raise

    async def _publish_workspace(
        self,
        workspace: Path,
        output_dir: Path,
    ) -> None:
        lock = await self._lock_for(
            output_dir
        )

        async with lock:
            backup = (
                output_dir.parent
                / (
                    f".{output_dir.name}."
                    f"backup-{uuid4().hex}"
                )
            )

            moved_old = False

            try:
                if output_dir.exists():
                    output_dir.rename(
                        backup
                    )
                    moved_old = True

                workspace.rename(
                    output_dir
                )

            except Exception:
                if (
                    output_dir.exists()
                    and not workspace.exists()
                ):
                    shutil.rmtree(
                        output_dir,
                        ignore_errors=True,
                    )

                if (
                    moved_old
                    and backup.exists()
                    and not output_dir.exists()
                ):
                    backup.rename(
                        output_dir
                    )

                raise

            else:
                if backup.exists():
                    shutil.rmtree(
                        backup,
                        ignore_errors=True,
                    )

    async def _lock_for(
        self,
        output_dir: Path,
    ) -> asyncio.Lock:
        key = str(
            output_dir.resolve()
        )

        async with self._locks_guard:
            lock = self._locks.get(
                key
            )

            if lock is None:
                lock = asyncio.Lock()
                self._locks[key] = lock

            return lock

    @staticmethod
    def _artifact_relative_paths(
        artifact: CartoonGenerationResult,
        workspace: Path,
    ) -> dict[str, Path]:
        fields = (
            "html_path",
            "video_path",
        )

        return {
            field: (
                getattr(
                    artifact,
                    field,
                )
                .resolve()
                .relative_to(
                    workspace.resolve()
                )
            )
            for field in fields
        }

    @staticmethod
    def _rebase_artifact(
        artifact: CartoonGenerationResult,
        output_dir: Path,
        relative_paths: dict[str, Path],
    ) -> CartoonGenerationResult:
        return CartoonGenerationResult(
            schema_version=artifact.schema_version,
            title=artifact.title,
            duration_ms=artifact.duration_ms,
            scene_count=artifact.scene_count,
            has_audio=artifact.has_audio,
            output_dir=output_dir,
            html_path=(
                output_dir
                / relative_paths["html_path"]
            ),
            video_path=(
                output_dir
                / relative_paths["video_path"]
            ),
        )

    @staticmethod
    def _build_generation_config(
        raw_config: dict[str, Any],
    ) -> CartoonGenerationConfig:
        return CartoonGenerationConfig.model_validate(
            {
                key: value
                for key, value in raw_config.items()
                if key != "agent_id"
            }
        )

    @staticmethod
    def _normalize_mapping(
        value: Any,
    ) -> dict[str, Any]:
        if not value:
            return {}

        if isinstance(
            value,
            BaseModel,
        ):
            value = value.model_dump(
                mode="json",
                exclude_none=True,
            )

        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                "upstream_handoffs 必须是字典"
            )

        return {
            str(key): CartoonService._json_value(
                item
            )
            for key, item in value.items()
        }

    @staticmethod
    def _json_value(
        value: Any,
    ) -> Any:
        if isinstance(
            value,
            BaseModel,
        ):
            return value.model_dump(
                mode="json",
                exclude_none=True,
            )

        if isinstance(
            value,
            dict,
        ):
            return {
                str(key): CartoonService._json_value(
                    item
                )
                for key, item in value.items()
            }

        if isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):
            return [
                CartoonService._json_value(
                    item
                )
                for item in value
            ]

        if (
            value is None
            or isinstance(
                value,
                (
                    str,
                    int,
                    float,
                    bool,
                ),
            )
        ):
            return value

        return str(value)

    @staticmethod
    def _source_materials(
        handoffs: dict[str, Any],
    ) -> list[str]:
        sections: list[str] = []

        for source, payload in handoffs.items():
            if not isinstance(
                payload,
                dict,
            ):
                sections.append(f"{source}\n{payload}")
                continue

            title = str(
                payload.get("title")
                or source
            )

            summary = str(
                payload.get(
                    "one_sentence_summary"
                )
                or payload.get("summary")
                or ""
            ).strip()

            materials = (
                payload.get("materials")
                or []
            )

            lines = [title]

            if summary:
                lines.extend(
                    [
                        "",
                        summary,
                    ]
                )

            for material in materials:
                text = str(
                    material
                ).strip()

                if text:
                    lines.extend(
                        [
                            "",
                            text,
                        ]
                    )

            sections.append(
                "\n".join(lines)
            )

        return [section[:4_000] for section in sections if section.strip()][:12]

    @staticmethod
    def _string_list(
        value: Any,
        limit: int,
    ) -> list[str]:
        if value is None:
            return []

        if isinstance(
            value,
            str,
        ):
            raw_items = [
                item.strip()
                for item in value
                .replace("，", ",")
                .split(",")
            ]

        elif isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):
            raw_items = [
                str(item).strip()
                for item in value
            ]

        else:
            raw_items = [
                str(value).strip()
            ]

        result: list[str] = []

        for item in raw_items:
            if item and item not in result:
                result.append(
                    item[:160]
                )

            if len(result) >= limit:
                break

        return result

    @staticmethod
    def _bounded_text(
        value: Any,
        limit: int,
    ) -> str:
        text = str(
            value
            or ""
        ).strip()

        return text[:limit]

    @staticmethod
    def _username(
        username: Any,
        user_id: Any,
    ) -> str:
        value = str(
            username
            or user_id
            or "anonymous"
        ).strip()

        safe = "".join(
            char
            for char in value
            if (
                char.isalnum()
                or char in {
                    "-",
                    "_",
                }
            )
        )

        return (
            safe[:80]
            or "anonymous"
        )

    @staticmethod
    def _build_card_result(
        artifact: CartoonGenerationResult,
        started: float,
    ) -> "AgentResult":
        from app.resource.schemas import (
            AgentResult,
        )

        duration_seconds = round(
            artifact.duration_ms / 1000,
            2,
        )

        card = {
            "schema_version": "cartoon/v6",
            "resource_type": "cartoon",
            "title": artifact.title,
            "file_type": "mp4",
            "video_url": static_url(
                artifact.video_path
            ),
            "preview_url": static_url(
                artifact.html_path
            ),
            "duration_seconds": duration_seconds,
            "scene_count": artifact.scene_count,
            "has_audio": artifact.has_audio,
            "engine": "hyperframes",
        }

        elapsed_ms = int(
            (
                time.perf_counter()
                - started
            )
            * 1000
        )

        return AgentResult(
            success=True,
            title=artifact.title,
            file_type="mp4",
            content=json.dumps(
                card,
                ensure_ascii=False,
            ),
            summary=(
                f"{artifact.scene_count} 个场景，"
                f"时长 {duration_seconds:.1f} 秒"
            ),
            metrics={
                "scene_count": artifact.scene_count,
                "duration_seconds": duration_seconds,
                "elapsed_ms": elapsed_ms,
            },
            metadata={
                "agent_id": "cartoon",
                "schema_version": "cartoon/v6",
                "engine": "hyperframes",
                "has_audio": artifact.has_audio,
                "video_file_path": str(artifact.video_path),
                "html_file_path": str(artifact.html_path),
                "video_url": static_url(
                    artifact.video_path
                ),
                "html_url": static_url(
                    artifact.html_path
                ),
            },
        )

    @staticmethod
    def _build_error_result(
        title_source: str,
        exc: CartoonGenerationError,
        started: float,
    ) -> "AgentResult":
        from app.resource.schemas import (
            AgentResult,
        )

        elapsed_ms = int(
            (
                time.perf_counter()
                - started
            )
            * 1000
        )

        logger.error(
            (
                "Cartoon generation failed: "
                "stage=%s error=%s elapsed_ms=%d"
            ),
            exc.stage,
            exc,
            elapsed_ms,
        )

        return AgentResult(
            success=False,
            title=(
                f"{title_source[:48]} "
                f"- 动画讲解视频"
            ),
            file_type="mp4",
            error=str(exc),
            metrics={
                "elapsed_ms": elapsed_ms,
            },
            metadata={
                "agent_id": "cartoon",
                "stage": exc.stage,
                "problems": exc.problems,
            },
        )
