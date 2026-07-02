"""Frontend Slides HTML presentation agent."""

from __future__ import annotations

import uuid

from app.infra.logging import get_logger
from app.config import WORKPLACE_DIR
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.shared.ppt import (
    PresentationGenerationError,
    PresentationPipeline,
)
from app.shared.ppt.storage import PresentationPublisher
from app.shared.ppt.schemas import (
    SourceArtifact,
    ResourcePPTRequest,
    PathPPTRequest,
)
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


def build_resource_ppt_request(input_data: ResourceInput) -> ResourcePPTRequest:
    return ResourcePPTRequest(
        learning_need=input_data.learning_need,
        learning_scenario=input_data.learning_scenario,
        profile=input_data.profile or {},
        teaching_plan=(
            input_data.teaching_plan.model_dump(mode="json")
            if input_data.teaching_plan
            else None
        ),
        artifacts=_source_artifacts(input_data.upstream_handoffs),
    )


def build_path_ppt_request(input_data: NodeInput) -> PathPPTRequest:
    return PathPPTRequest(
        learning_need=input_data.learning_need,
        profile=input_data.profile or {},
        artifacts=_result_artifacts(input_data.existing_resources),
        path_title=input_data.path_title,
        path_goal=input_data.path_goal,
        node_title=input_data.node_title,
        node_key=input_data.node_id,
        difficulty=input_data.difficulty,
        knowledge_points=list(input_data.knowledge_points or []),
        weak_knowledge_points=list(input_data.weak_knowledge_points or []),
        generation_focus=list(input_data.generation_focus or []),
        tutorial_title=input_data.tutorial_title,
        tutorial_summary=input_data.tutorial_summary,
        tutorial_markdown=input_data.tutorial_markdown,
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
            build_path_ppt_request(input_data),
            file_id=f"node_{input_data.node_id}",
            prompt_prefix="path",
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
        # 动态构建 publisher，使用统一路径 resource/{userId}/{resourceId}/
        user_id = input_data.user_id or 0
        output_dir = WORKPLACE_DIR / "resource" / str(user_id) / str(input_data.resource_id or file_id)
        publisher = PresentationPublisher(output_dir)
        pipeline = PresentationPipeline(publisher=publisher)
        return await self._generate(
            build_resource_ppt_request(input_data),
            file_id=file_id,
            prompt_prefix="resource",
            pipeline=pipeline,
        )

    async def _generate(
        self,
        request: ResourcePPTRequest | PathPPTRequest,
        *,
        file_id: str,
        prompt_prefix: str,
        pipeline: PresentationPipeline | None = None,
    ) -> AgentResult:
        async def progress(message: str, percent: int) -> None:
            await self.emitter.send(self.agent_id, "running", message, percent)

        try:
            artifact = await (pipeline or self.pipeline).generate(
                request,
                file_id=file_id,
                prompt_prefix=prompt_prefix,
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
        )
