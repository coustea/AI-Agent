"""Frontend Slides HTML presentation agent."""

from __future__ import annotations

import uuid

from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.ppt_pipeline import (
    PresentationGenerationError,
    PresentationPipeline,
)
from app.resource.agents.ppt_pipeline.schemas import SourceArtifact, SourcePack
from app.resource.schemas import (
    AgentResult,
    DownstreamContext,
    NodeInput,
    ResourceInput,
    ReusableAssets,
)

logger = get_logger(__name__)


def _source_artifacts(
    handoffs: dict[str, DownstreamContext],
) -> list[SourceArtifact]:
    artifacts: list[SourceArtifact] = []
    for agent_id, handoff in handoffs.items():
        materials = [
            handoff.one_sentence_summary,
            *handoff.reusable_assets.examples[:4],
            *handoff.reusable_assets.visual_ideas[:4],
        ]
        deduped = list(
            dict.fromkeys(str(item).strip() for item in materials if str(item).strip())
        )
        artifacts.append(
            SourceArtifact(
                agent_id=agent_id,
                title=handoff.title or agent_id,
                summary=handoff.one_sentence_summary or handoff.title or agent_id,
                materials=deduped[:12],
            )
        )
    return artifacts


def _result_artifacts(results: dict[str, AgentResult]) -> list[SourceArtifact]:
    return [
        SourceArtifact(
            agent_id=agent_id,
            title=result.title or agent_id,
            summary=result.summary or result.title or agent_id,
            materials=[result.content[:4000]] if result.content.strip() else [],
        )
        for agent_id, result in results.items()
        if result.success
    ]


def build_resource_source_pack(input_data: ResourceInput) -> SourcePack:
    return SourcePack(
        learning_need=input_data.learning_need,
        learning_scenario=input_data.learning_scenario,
        profile=input_data.profile or {},
        teaching_plan=(
            input_data.teaching_plan.model_dump(mode="json")
            if input_data.teaching_plan
            else None
        ),
        source_type="resource",
        artifacts=_source_artifacts(input_data.upstream_handoffs),
    )


def build_node_source_pack(input_data: NodeInput) -> SourcePack:
    return SourcePack(
        learning_need=input_data.learning_need,
        learning_scenario="self_study",
        profile=input_data.profile or {},
        teaching_plan=None,
        source_type="node",
        artifacts=_result_artifacts(input_data.existing_resources),
        node_context={
            "path_title": input_data.path_title,
            "path_goal": input_data.path_goal,
            "node_title": input_data.node_title,
            "node_key": input_data.node_key,
            "difficulty": input_data.difficulty,
            "knowledge_points": input_data.knowledge_points,
            "weak_knowledge_points": input_data.weak_knowledge_points,
            "generation_focus": input_data.generation_focus,
            "tutorial_title": input_data.tutorial_title,
            "tutorial_summary": input_data.tutorial_summary,
            "tutorial_markdown": input_data.tutorial_markdown,
        },
    )


@register_agent
class PPTAgent(BaseResourceAgent):
    agent_id = "ppt"
    agent_name = "教学课件"

    def __init__(self, emitter=None, pipeline: PresentationPipeline | None = None):
        super().__init__(emitter=emitter)
        self.pipeline = pipeline or PresentationPipeline()

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        return await self._generate(
            build_node_source_pack(input_data),
            file_id=f"node_{input_data.node_id}",
        )

    async def generate_resource(
        self,
        input_data: ResourceInput | NodeInput,
    ) -> AgentResult:
        if isinstance(input_data, NodeInput):
            return await self.generate_node(input_data)
        file_id = (
            str(input_data.resource_id)
            if input_data.resource_id is not None
            else uuid.uuid4().hex
        )
        return await self._generate(
            build_resource_source_pack(input_data),
            file_id=file_id,
        )

    async def _generate(
        self,
        source_pack: SourcePack,
        *,
        file_id: str,
    ) -> AgentResult:
        async def progress(message: str, percent: int) -> None:
            await self.emitter.send(self.agent_id, "running", message, percent)

        try:
            artifact = await self.pipeline.generate(
                source_pack,
                file_id=file_id,
                progress=progress,
            )
        except PresentationGenerationError as exc:
            logger.error(
                "PPT validation failed after repair: static=%s visual=%s",
                exc.static_audit.problems,
                [problem.model_dump() for problem in exc.visual_audit.problems],
            )
            return AgentResult(
                success=False,
                title="PPT 生成失败",
                file_type="html",
                error=str(exc),
                metadata={"agent_id": self.agent_id},
            )
        except Exception as exc:
            logger.exception("PPT pipeline failed")
            return AgentResult(
                success=False,
                title="PPT 生成失败",
                file_type="html",
                error=str(exc),
                metadata={"agent_id": self.agent_id},
            )

        title = artifact.brief.purpose
        path = artifact.path
        return AgentResult(
            success=True,
            title=f"{title} - 教学课件",
            file_type="html",
            content="",
            summary=f"生成 {artifact.slide_count} 页 HTML 教学课件",
            metrics={"slide_count": artifact.slide_count},
            metadata={
                "agent_id": self.agent_id,
                "html_file_path": str(path),
                "html_url": f"/api/v1/ai/resources/public/{file_id}/html",
                "slide_count": artifact.slide_count,
                "style_name": artifact.style.selected.name,
                "density": artifact.brief.density,
                "file_size": path.stat().st_size,
            },
            downstream_context=DownstreamContext(
                source_agent=self.agent_id,
                title=title,
                one_sentence_summary=(
                    f"{title} - {artifact.slide_count} 页 HTML 教学课件"
                ),
                reusable_assets=ReusableAssets(),
                covered_outline_ids=[],
            ),
        )
