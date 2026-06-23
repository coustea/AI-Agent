"""教学课件生成 Agent。

专注于计算机专业理论的语义层策划，直接生成 SlideIntent 语义文档。
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.config import INFERENCE_TEMPERATURE
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.prompts import prompts
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import outline_coverage_summary
from app.resource.ppt_contract import (
    ExplanationStyle,
    PptDocument,
    ThemeId,
    VisualEmphasis,
)
from app.resource.schemas import AgentResult, DownstreamContext, NodeInput, ResourceInput

logger = get_logger(__name__)


class NodeMaterialContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path_title: str = ""
    path_goal: str = ""
    node_title: str = ""
    node_key: str = ""
    difficulty: str | None = None
    knowledge_points: list[str] = Field(default_factory=list)
    weak_knowledge_points: list[str] = Field(default_factory=list)
    generation_focus: list[str] = Field(default_factory=list)
    tutorial_title: str = ""
    tutorial_summary: str | None = None
    tutorial_markdown: str = ""


class SourceArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str
    title: str
    summary: str
    materials: list[str] = Field(default_factory=list, max_length=12)


class SourcePack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learning_need: str
    learning_scenario: str
    profile: dict[str, Any] | str
    teaching_plan: dict[str, Any] | None
    source_type: Literal["resource", "node"]
    artifacts: list[SourceArtifact]
    node_context: NodeMaterialContext | None = None


def _artifact_from_handoff(agent_id: str, handoff: DownstreamContext) -> SourceArtifact:
    materials = [handoff.one_sentence_summary] if handoff.one_sentence_summary else []
    materials.extend(handoff.reusable_assets.examples[:4])
    materials.extend(handoff.reusable_assets.visual_ideas[:4])
    deduped_materials: list[str] = []
    for item in materials:
        text = str(item).strip()
        if text and text not in deduped_materials:
            deduped_materials.append(text)
    return SourceArtifact(
        agent_id=agent_id,
        title=handoff.title or agent_id,
        summary=handoff.one_sentence_summary or handoff.title or agent_id,
        materials=deduped_materials[:12],
    )


def build_resource_source_pack(input_data: ResourceInput) -> SourcePack:
    artifacts = [
        _artifact_from_handoff(agent_id, handoff)
        for agent_id, handoff in input_data.upstream_handoffs.items()
    ]
    return SourcePack(
        learning_need=input_data.learning_need,
        learning_scenario=input_data.learning_scenario,
        profile=input_data.profile or {},
        teaching_plan=input_data.teaching_plan.model_dump(mode="json") if input_data.teaching_plan else None,
        source_type="resource",
        artifacts=artifacts,
    )


def build_node_source_pack(input_data: NodeInput) -> SourcePack:
    node_context = NodeMaterialContext(
        path_title=input_data.path_title,
        path_goal=input_data.path_goal,
        node_title=input_data.node_title,
        node_key=input_data.node_key,
        difficulty=input_data.difficulty,
        knowledge_points=input_data.knowledge_points,
        weak_knowledge_points=input_data.weak_knowledge_points,
        generation_focus=input_data.generation_focus,
        tutorial_title=input_data.tutorial_title,
        tutorial_summary=input_data.tutorial_summary,
        tutorial_markdown=input_data.tutorial_markdown,
    )
    materials = [
        item
        for item in [input_data.tutorial_summary or "", input_data.tutorial_markdown]
        if str(item).strip()
    ]
    artifacts = [
        SourceArtifact(
            agent_id="content",
            title=input_data.tutorial_title or input_data.node_title,
            summary=input_data.tutorial_summary or input_data.node_title,
            materials=materials[:12],
        )
    ]
    return SourcePack(
        learning_need=input_data.node_title,
        learning_scenario="path_learning",
        profile=input_data.profile or {},
        teaching_plan=None,
        source_type="node",
        artifacts=artifacts,
        node_context=node_context,
    )


@register_agent
class PptAgent(BaseResourceAgent):
    """教学课件生成 Agent。"""

    agent_id = "ppt"
    agent_name = "教学课件"

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        source_pack = build_resource_source_pack(input_data)
        title_prefix = input_data.learning_need[:32]
        ppt_config = self._resolve_ppt_config(input_data.agent_config)
        result = await self._run_pipeline(
            source_pack=source_pack,
            theme_id=ppt_config["theme_id"],
            explanation_style=ppt_config["explanation_style"],
            visual_emphasis=ppt_config["visual_emphasis"],
            title_prefix=title_prefix,
        )
        if result.success:
            coverage = outline_coverage_summary(input_data.teaching_plan, input_data.upstream_handoffs)
            result.metadata["teaching_plan_outline_ids"] = coverage["teaching_plan_outline_ids"]
            result.metadata["covered_source_outline_ids"] = coverage["covered_source_outline_ids"]
            result.metadata["missing_source_outline_ids"] = coverage["missing_source_outline_ids"]
        await self.events.send_agent_status(self.agent_id, status="completed" if result.success else "failed", message=result.summary if result.success else (result.error or f"{self.agent_name}生成失败"), progress=100 if result.success else 0)
        return result

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        source_pack = build_node_source_pack(input_data)
        ppt_config = self._resolve_ppt_config(input_data.agent_config)
        result = await self._run_pipeline(
            source_pack=source_pack,
            theme_id=ppt_config["theme_id"],
            explanation_style=ppt_config["explanation_style"],
            visual_emphasis=ppt_config["visual_emphasis"],
            title_prefix=input_data.node_title,
        )
        result.metadata["path_id"] = input_data.path_id
        result.metadata["node_id"] = input_data.node_id
        await self.events.send_agent_status(self.agent_id, status="completed" if result.success else "failed", message=result.summary if result.success else (result.error or f"{self.agent_name}生成失败"), progress=100 if result.success else 0)
        return result

    async def _run_pipeline(
        self,
        *,
        source_pack: SourcePack,
        theme_id: ThemeId,
        explanation_style: ExplanationStyle,
        visual_emphasis: VisualEmphasis,
        title_prefix: str,
    ) -> AgentResult:
        logger.info(
            "PptAgent semantic pipeline start: source_type=%s theme=%s style=%s emphasis=%s",
            source_pack.source_type,
            theme_id,
            explanation_style,
            visual_emphasis,
        )
        try:
            await self.events.send_agent_step(self.agent_id, phase="start", message="正在规划并生成教学课件语义结构与关系", progress=40)
            
            input_data = {
                "source_pack": source_pack.model_dump(mode="json"),
                "theme_id": theme_id,
                "explanation_style": explanation_style,
                "visual_emphasis": visual_emphasis,
            }
            
            prompt = prompts.get("resource").get("ppt_director")
            document = await get_llm().ainvoke_json(
                PptDocument,
                f"{prompt}\n\n{json.dumps(input_data, ensure_ascii=False)}",
                temperature=INFERENCE_TEMPERATURE,
                max_tokens=6000,
                max_attempts=1,
                prompt_fallback=False,
            )
            
            await self.events.send_agent_step(self.agent_id, phase="start", message="课件语义结构生成完毕", progress=90)
            
        except Exception as exc:
            logger.error("PptAgent generation failed: %s", exc, exc_info=True)
            return AgentResult(
                success=False,
                title=f"{title_prefix} - 教学课件",
                summary=f"课件生成失败: {exc}",
                error=str(exc),
                metadata={"agent_id": "ppt"},
            )

        return AgentResult(
            success=True,
            content=document.model_dump_json(indent=2),
            file_type="json",
            title=f"{title_prefix} - 教学课件",
            summary=f"生成 {len(document.slides)} 页教学课件意图",
            metrics={
                "page_count": len(document.slides),
            },
            metadata={"agent_id": "ppt"},
        )

    def _resolve_ppt_config(self, config: dict[str, Any] | None) -> dict[str, str]:
        """解析 PPT 配置，返回 theme_id、explanation_style、visual_emphasis。"""
        if not config:
            config = {}
        # 默认使用学术风格和平衡可视化
        return {
            "theme_id": config.get("theme_id", "technical-blueprint"),
            "explanation_style": config.get("explanation_style", "conceptual"),
            "visual_emphasis": config.get("visual_emphasis", "balanced"),
        }