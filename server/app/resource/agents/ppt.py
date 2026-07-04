"""HTML PPT agent for standalone resources and learning-path nodes."""

from __future__ import annotations

import uuid
from pathlib import Path

from app.config import (
    path_node_ppt_url,
    resource_ppt_url,
    user_path_node_ppt_dir,
    user_resource_ppt_dir,
)
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.shared.ppt import (
    PathPPTRequest,
    PPTGenerationError,
    PPTGenerator,
    PPTPreferences,
    PPTSource,
    ResourcePPTRequest,
)
from app.resource.schemas import (
    AgentResult,
    DownstreamContext,
    NodeInput,
    ResourceInput,
)

logger = get_logger(__name__)


def _source_artifacts(
    handoffs: dict[str, DownstreamContext],
) -> list[PPTSource]:
    artifacts: list[PPTSource] = []
    for agent_id, handoff in handoffs.items():
        materials = [
            *handoff.materials,
            *handoff.reusable_assets.examples[:4],
            *handoff.reusable_assets.visual_ideas[:4],
        ]
        deduped = list(
            dict.fromkeys(str(item).strip() for item in materials if str(item).strip())
        )
        artifacts.append(
            PPTSource(
                agent_id=agent_id,
                title=handoff.title or agent_id,
                summary=handoff.one_sentence_summary or handoff.title or agent_id,
                materials=deduped[:12],
            )
        )
    return artifacts


def _result_artifacts(results: dict[str, AgentResult]) -> list[PPTSource]:
    return [
        PPTSource(
            agent_id=agent_id,
            title=result.title or agent_id,
            summary=result.summary or result.title or agent_id,
            materials=[result.content[:4000]] if result.content.strip() else [],
        )
        for agent_id, result in results.items()
        if result.success
    ]


def build_resource_ppt_request(input_data: ResourceInput) -> ResourcePPTRequest:
    preferences = PPTPreferences.model_validate(
        {
            key: value
            for key, value in input_data.agent_config.items()
            if key != "agent_id"
        }
    )
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
        preferences=preferences,
    )


def build_path_ppt_request(input_data: NodeInput) -> PathPPTRequest:
    preferences = PPTPreferences.model_validate(
        {
            key: value
            for key, value in input_data.agent_config.items()
            if key != "agent_id"
        }
    )
    return PathPPTRequest(
        learning_need=input_data.node_title,
        profile=input_data.profile or {},
        artifacts=_result_artifacts(input_data.existing_resources),
        path_title=input_data.path_title,
        path_goal=input_data.path_goal,
        node_title=input_data.node_title,
        node_key=input_data.node_key or str(input_data.node_id),
        difficulty=input_data.difficulty or "beginner",
        knowledge_points=list(input_data.knowledge_points or []),
        weak_knowledge_points=list(input_data.weak_knowledge_points or []),
        generation_focus=list(input_data.generation_focus or []),
        tutorial_title=input_data.tutorial_title,
        tutorial_summary=input_data.tutorial_summary or input_data.node_title,
        tutorial_markdown=input_data.tutorial_markdown,
        preferences=preferences,
    )


@register_agent
class PPTAgent(BaseResourceAgent):
    """Adapt resource and path inputs to the shared PPT Module."""

    agent_id = "ppt"
    agent_name = "演示幻灯"
    research_enabled = False

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        username = input_data.username or "anonymous"
        output_dir = user_path_node_ppt_dir(
            username, str(input_data.path_id), str(input_data.node_id)
        )
        return await self._generate(
            build_path_ppt_request(input_data),
            output_dir=output_dir,
            html_url=path_node_ppt_url(
                username,
                str(input_data.path_id),
                str(input_data.node_id),
            ),
        )

    async def generate_resource(
        self,
        input_data: ResourceInput | NodeInput,
    ) -> AgentResult:
        if isinstance(input_data, NodeInput):
            return await self.generate_node(input_data)
        resource_key = (
            str(input_data.resource_id)
            if input_data.resource_id is not None
            else uuid.uuid4().hex
        )
        username = input_data.username or str(input_data.user_id or "anonymous")
        output_dir = user_resource_ppt_dir(username, resource_key)
        return await self._generate(
            build_resource_ppt_request(input_data),
            output_dir=output_dir,
            html_url=resource_ppt_url(username, resource_key),
        )

    async def _generate(
        self,
        request: ResourcePPTRequest | PathPPTRequest,
        *,
        output_dir: Path,
        html_url: str,
    ) -> AgentResult:
        async def progress(message: str, percent: int) -> None:
            await self.emitter.send(self.agent_id, "running", message, percent)

        try:
            artifact = await PPTGenerator().generate(
                request,
                output_dir=output_dir,
                progress=progress,
            )
        except PPTGenerationError as exc:
            logger.exception("PPT generation failed")
            return AgentResult(
                success=False,
                title="PPT 生成失败",
                file_type="html",
                error=str(exc),
                metadata={
                    "agent_id": self.agent_id,
                    "generation_stage": exc.stage,
                },
            )

        title = artifact.plan.title
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
                "html_url": html_url,
                "slide_count": artifact.slide_count,
                "style_name": artifact.template_name,
                "template_id": artifact.template_id,
                "density": artifact.plan.density,
                "file_size": path.stat().st_size,
            },
        )
