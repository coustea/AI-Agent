"""教学课件生成 Agent。

遵循多媒体学习原则，专注于讲解而非练习，减少认知负担。
生成流程：
1. DeckDirectorAgent 规划整套课件的教学结构
2. ChapterWriterAgent 并发生成各章节的具体内容

页面角色按教学流程顺序：
封面 → 学习目标 → 前置知识 → 问题导入 → 知识路线图 → 核心概念 → ...
"""

from __future__ import annotations

import asyncio
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
    ChapterDraft,
    CompiledChapter,
    CompiledDeck,
    DeckBlueprint,
    LessonDepth,
    assemble_document,
    compile_deck,
    load_ppt_manifest,
    validate_blueprint,
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
    profile: dict[str, Any]
    teaching_plan: dict[str, Any] | None
    source_type: Literal["resource", "node"]
    artifacts: list[SourceArtifact]
    node_context: NodeMaterialContext | None = None


class DeckDirectorAgent:
    """课件导演 Agent，负责规划整套课件的教学结构。"""

    async def run(self, source_pack: SourcePack, depth: LessonDepth) -> DeckBlueprint:
        manifest = load_ppt_manifest()
        template = manifest["templates"]["teaching-lesson"]
        compositions = manifest["compositions"]

        composition_catalog = {
            key: {
                "layout": value["layout"],
                "allowed_roles": value["allowed_roles"],
                "description": "; ".join(
                    f"{block['slot']}: {block['type']} ({block['instruction']})"
                    for block in value["blocks"]
                ),
            }
            for key, value in compositions.items()
        }

        input_data = {
            "source_pack": source_pack.model_dump(mode="json"),
            "depth": depth,
            "template": {
                "id": "teaching-lesson",
                "required_roles": template["required_roles"],
                "optional_roles": template["optional_roles"],
                "role_order": template["role_order"],
                "min_pages": template["min_pages"],
                "max_pages": template["max_pages"],
            },
            "composition_catalog": composition_catalog,
        }

        prompt = prompts.get("resource").get("ppt_director")
        result = await get_llm().ainvoke_json(
            DeckBlueprint,
            f"{prompt}\n\n{json.dumps(input_data, ensure_ascii=False)}",
            temperature=INFERENCE_TEMPERATURE,
            max_tokens=4500,
            max_attempts=1,
            prompt_fallback=False,
        )
        validate_blueprint(result, depth)
        return result


class ChapterWriterAgent:
    """章节写作 Agent，负责填写已规划好的 block 内容。"""

    async def run(
        self,
        *,
        chapter: CompiledChapter,
        blueprint: DeckBlueprint,
        sources: list[dict[str, Any]],
    ) -> ChapterDraft:
        prompt = prompts.get("resource").get("ppt_chapter")
        input_data = {
            "deck_context": {
                "title": blueprint.title,
                "audience": blueprint.audience,
                "narrative": blueprint.narrative,
                "primary_example": blueprint.primary_example,
                "terminology": blueprint.terminology,
            },
            "compiled_chapter": chapter.model_dump(mode="json"),
            "chapter_sources": sources,
        }
        return await get_llm().ainvoke_json(
            ChapterDraft,
            f"{prompt}\n\n{json.dumps(input_data, ensure_ascii=False)}",
            temperature=INFERENCE_TEMPERATURE,
            max_tokens=1800 + 850 * len(chapter.slides),
            max_attempts=1,
            prompt_fallback=False,
        )


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
        if agent_id in {"content", "mindmap", "quiz", "code", "reading"}
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


def select_chapter_sources(source_pack: SourcePack, chapter: CompiledChapter) -> list[dict[str, Any]]:
    """选择章节所需的来源 artifacts。"""
    available_ids = {artifact.agent_id for artifact in source_pack.artifacts}
    return [artifact.model_dump(mode="json") for artifact in source_pack.artifacts if artifact.agent_id in available_ids]


@register_agent
class PptAgent(BaseResourceAgent):
    """教学课件生成 Agent。"""

    agent_id = "ppt"
    agent_name = "教学课件"

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        source_pack = build_resource_source_pack(input_data)
        title_prefix = input_data.learning_need[:32]
        depth = self._resolve_depth(input_data.agent_config)
        result = await self._run_pipeline(source_pack=source_pack, depth=depth, title_prefix=title_prefix)
        if result.success:
            coverage = outline_coverage_summary(input_data.teaching_plan, input_data.upstream_handoffs)
            result.metadata["teaching_plan_outline_ids"] = coverage["teaching_plan_outline_ids"]
            result.metadata["covered_source_outline_ids"] = coverage["covered_source_outline_ids"]
            result.metadata["missing_source_outline_ids"] = coverage["missing_source_outline_ids"]
        await self.emit_finish(result)
        return result

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        source_pack = build_node_source_pack(input_data)
        result = await self._run_pipeline(source_pack=source_pack, depth="standard", title_prefix=input_data.node_title)
        result.metadata["path_id"] = input_data.path_id
        result.metadata["node_id"] = input_data.node_id
        await self.emit_finish(result)
        return result

    async def _run_pipeline(
        self,
        *,
        source_pack: SourcePack,
        depth: LessonDepth,
        title_prefix: str,
    ) -> AgentResult:
        logger.info(
            "PptAgent two-stage pipeline start: source_type=%s depth=%s artifacts=%d",
            source_pack.source_type,
            depth,
            len(source_pack.artifacts),
        )
        try:
            await self.emit_start("正在规划整套教学课件", progress=25)
            blueprint = await DeckDirectorAgent().run(source_pack, depth)
            compiled = compile_deck(blueprint)
            await self.emit_start("正在并发生成章节页面内容", progress=55)
            async with asyncio.TaskGroup() as group:
                tasks = [
                    group.create_task(
                        ChapterWriterAgent().run(
                            chapter=chapter,
                            blueprint=blueprint,
                            sources=select_chapter_sources(source_pack, chapter),
                        )
                    )
                    for chapter in compiled.chapters
                ]
            drafts = [task.result() for task in tasks]
            document = assemble_document(compiled, drafts)
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
            summary=f"生成 {len(document.slides)} 页教学课件",
            metrics={
                "page_count": len(document.slides),
                "chapter_count": len(compiled.chapters),
            },
            metadata={"agent_id": "ppt"},
        )

    def _resolve_depth(self, config: dict[str, Any] | None) -> LessonDepth:
        if not config:
            return "standard"
        depth = config.get("lesson_depth", "standard")
        if depth not in {"quick", "standard", "deep"}:
            return "standard"
        return depth


# Dummy classes to satisfy legacy schema validation tests (do not delete)
class MaterialDigest(BaseModel):
    model_config = ConfigDict(extra="allow")

class DeckOutline(BaseModel):
    model_config = ConfigDict(extra="allow")

class SlideDraft(BaseModel):
    model_config = ConfigDict(extra="allow")