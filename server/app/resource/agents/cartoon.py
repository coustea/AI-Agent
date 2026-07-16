"""Resource-domain adapter for verified cartoon generation."""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from app.config import static_url, user_resource_cartoon_dir
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.schemas import AgentResult, ResourceInput
from app.shared.cartoon import (
    CartoonBrief,
    CartoonGenerationConfig,
    CartoonGenerationError,
    CartoonPipeline,
    CartoonResourceMetadata,
)


logger = get_logger(__name__)


@register_agent
class CartoonAgent(BaseResourceAgent):
    agent_id = "cartoon"
    agent_name = "动画讲解"

    def __init__(self, emitter=None, *, pipeline: CartoonPipeline | None = None) -> None:
        super().__init__(emitter=emitter)
        self._pipeline = pipeline or CartoonPipeline()

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        return await self.run_with_heartbeat(
            self._generate(input_data),
            messages=["正在设计语义分镜...", "正在合成配音、字幕与动画..."],
            interval_seconds=15.0,
            progress=75,
        )

    async def _generate(self, input_data: ResourceInput) -> AgentResult:
        started = time.perf_counter()
        try:
            brief = self._brief(input_data)
            username = self._safe_username(input_data.username or input_data.user_id)
            resource_key = str(input_data.resource_id) if input_data.resource_id is not None else uuid4().hex
            artifact = await self._pipeline.generate(
                brief,
                user_resource_cartoon_dir(username, resource_key),
            )
            return self._result(artifact, started)
        except CartoonGenerationError as exc:
            return self._failure(input_data.learning_need, exc, started)
        except Exception as exc:
            logger.exception("Resource cartoon generation failed")
            wrapped = CartoonGenerationError(
                f"动画资源生成异常: {exc}",
                stage="resource-adapter",
                problems=[str(exc)],
            )
            return self._failure(input_data.learning_need, wrapped, started)

    @staticmethod
    def _brief(input_data: ResourceInput) -> CartoonBrief:
        if input_data.teaching_plan is None:
            raise CartoonGenerationError(
                "资源动画缺少结构化教学计划",
                stage="request",
            )
        try:
            task = input_data.teaching_plan.task_for("cartoon")
        except KeyError as exc:
            raise CartoonGenerationError(
                "教学计划未给 cartoon Agent 分配任务",
                stage="request",
                problems=[str(exc)],
            ) from exc
        raw_config = dict(input_data.agent_config or {})
        config_fields = set(CartoonGenerationConfig.model_fields)
        configuration = CartoonGenerationConfig.model_validate(
            {key: value for key, value in raw_config.items() if key in config_fields}
        )
        return CartoonBrief(
            learning_need=input_data.learning_need.strip()[:500],
            instruction_context={
                "entry": "resource",
                "learner_goal": input_data.teaching_plan.learner_goal,
                "scope": input_data.teaching_plan.scope,
                "task": task.model_dump(mode="json"),
            },
            source_materials=CartoonAgent._source_materials(input_data.upstream_handoffs),
            knowledge_points=CartoonAgent._strings(raw_config.get("knowledge_points"), 30),
            weak_knowledge_points=CartoonAgent._strings(raw_config.get("weak_knowledge_points"), 20),
            configuration=configuration,
        )

    @staticmethod
    def _source_materials(handoffs: dict[str, Any]) -> list[str]:
        sections: list[str] = []
        for source, raw in (handoffs or {}).items():
            payload = raw.model_dump(mode="json") if isinstance(raw, BaseModel) else raw
            if not isinstance(payload, dict):
                sections.append(f"{source}\n{payload}"[:4_000])
                continue
            lines = [str(payload.get("title") or source)]
            summary = str(payload.get("one_sentence_summary") or "").strip()
            if summary:
                lines.extend(["", summary])
            for material in payload.get("materials") or []:
                value = str(material).strip()
                if value:
                    lines.extend(["", value])
            sections.append("\n".join(lines)[:4_000])
        return sections[:12]

    @staticmethod
    def _strings(value: Any, limit: int) -> list[str]:
        if value is None:
            return []
        raw = value.replace("，", ",").split(",") if isinstance(value, str) else list(value)
        result: list[str] = []
        for item in raw:
            normalized = str(item).strip()[:160]
            if normalized and normalized not in result:
                result.append(normalized)
            if len(result) == limit:
                break
        return result

    @staticmethod
    def _safe_username(value: Any) -> str:
        safe = "".join(char for char in str(value or "anonymous") if char.isalnum() or char in "-_")
        return safe[:80] or "anonymous"

    @staticmethod
    def _result(artifact: Any, started: float) -> AgentResult:
        duration_seconds = round(artifact.duration_ms / 1_000, 2)
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
