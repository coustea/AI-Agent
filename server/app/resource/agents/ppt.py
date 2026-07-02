"""教学课件生成 Agent - 完全对齐前端 PPTDocument 结构。

直接生成前端兼容的 JSON，包含 slots、blocks、takeaway 等字段。
"""

from __future__ import annotations

import json
import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.config import INFERENCE_TEMPERATURE
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.prompts import prompts
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import outline_coverage_summary
from app.resource.ppt_contract import PPTDocument, PptSlide, ThemeType
from app.resource.html_generator.generator import HTMLSlideGenerator
from app.resource.schemas import AgentResult, DownstreamContext, NodeInput, ResourceInput, ReusableAssets

logger = get_logger(__name__)


class NodeMaterialContext(BaseModel):
    """节点学习材料上下文"""
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
    """源材料"""
    model_config = ConfigDict(extra="forbid")

    agent_id: str
    title: str
    summary: str
    materials: list[str] = Field(default_factory=list, max_length=12)


class SourcePack(BaseModel):
    """PPT 生成输入源"""
    model_config = ConfigDict(extra="forbid")

    learning_need: str
    learning_scenario: str
    profile: dict[str, Any] | str
    teaching_plan: dict[str, Any] | None
    source_type: str
    artifacts: list[SourceArtifact]
    node_context: NodeMaterialContext | None = None


def _artifact_from_handoff(agent_id: str, handoff: DownstreamContext) -> SourceArtifact:
    """从 handoff 创建源材料"""
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
    """构建独立资源生成的源材料"""
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
    """构建节点学习材料源"""
    node_context = NodeMaterialContext(
        path_title=input_data.path_title,
        path_goal=input_data.path_goal,
        node_title=input_data.node_title,
        node_key=input_data.node_key,
        difficulty=input_data.difficulty,
        knowledge_points=input_data.knowledge_points or [],
        weak_knowledge_points=input_data.weak_knowledge_points or [],
        generation_focus=input_data.generation_focus or [],
        tutorial_title=input_data.tutorial_title,
        tutorial_summary=input_data.tutorial_summary,
        tutorial_markdown=input_data.tutorial_markdown,
    )
    artifacts = [
        _artifact_from_handoff(agent_id, handoff)
        for agent_id, handoff in input_data.upstream_handoffs.items()
    ]
    return SourcePack(
        learning_need=input_data.learning_need,
        learning_scenario=input_data.learning_scenario,
        profile=input_data.profile or {},
        teaching_plan=None,
        source_type="node",
        artifacts=artifacts,
        node_context=node_context,
    )


@register_agent
class PPTAgent(BaseResourceAgent):
    """PPT 生成 Agent - 生成前端兼容的 PPTDocument JSON"""
    
    agent_id = "ppt"
    agent_name = "教学课件"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        """路径节点资源生成入口 — 生成 PPTX 课件。

        由路径规划模块调用，为学习路径节点生成辅助 PPT 资源。
        """
        # 复用 generate_resource 的逻辑，传入 NodeInput
        return await self.generate_resource(input_data)

    async def generate_resource(self, input_data: ResourceInput | NodeInput) -> AgentResult:
        """生成 PPT 课件"""
        # 构建源材料
        if isinstance(input_data, NodeInput):
            source_pack = build_node_source_pack(input_data)
        else:
            source_pack = build_resource_source_pack(input_data)

        await self.emitter.send(self.agent_id, "running", "正在收集并组织讲义内容与大纲...", 15)

        # 准备 LLM 输入
        prompt_template = prompts.get("resource").get("ppt_chapter")
        if not prompt_template:
            return AgentResult(
                success=False,
                title="PPT 生成失败",
                file_type="json",
                content="",
                error="ppt_chapter 提示模板未找到",
            )

        # 调用 LLM 生成
        try:
            # 从 agent_config 读取 PPT 配置约束
            ppt_config = input_data.agent_config or {}
            theme_id = ppt_config.get("theme_id", "neon-cyber")
            explanation_style = ppt_config.get("explanation_style", "conceptual")
            visual_emphasis = ppt_config.get("visual_emphasis", "balanced")

            # 构建配置约束提示，确保 LLM 遵守用户选择
            config_hint = (
                f"\n\n## 用户配置约束（必须严格遵守）\n"
                f"- theme_id 必须为 \"{theme_id}\"，不得使用其他主题\n"
                f"- 讲解路线 (explanation_style): {explanation_style} "
                f"({'概念阐述优先' if explanation_style == 'conceptual' else '过程推演优先' if explanation_style == 'procedural' else '对比分析优先'})\n"
                f"- 视觉元素密度 (visual_emphasis): {visual_emphasis} "
                f"({'文字极简' if visual_emphasis == 'minimal' else '图文并茂' if visual_emphasis == 'balanced' else '图解加持'})\n"
            )

            await self.emitter.send(self.agent_id, "running", "正在调用AI大模型研制课件大纲与幻灯片页面结构...", 45)
            prompt = prompts.get("resource").render(
                "ppt_chapter",
                source_pack=json.dumps(source_pack.model_dump(mode="json"), ensure_ascii=False, indent=2),
                outline_coverage=outline_coverage_summary(input_data.teaching_plan, input_data.upstream_handoffs),
            ) + config_hint
            response = await self.llm.ainvoke(prompt)
            raw_content = response.content

            # 解析和验证 JSON
            try:
                from app.infra.utils import parse_first_json_object
                ppt_data = parse_first_json_object(raw_content)
                # 验证是否符合 PPTDocument schema
                await self.emitter.send(self.agent_id, "running", "正在校验 PPT 页面布局与排版结构...", 85)
                ppt_doc = PPTDocument.model_validate(ppt_data)

                # 【新增】生成 HTML 文件
                await self.emitter.send(self.agent_id, "running", "正在生成 HTML 幻灯片...", 90)
                
                # 安全获取 resource_id，兼容 NodeInput 场景
                res_id = getattr(input_data, "resource_id", None)
                if res_id is None:
                    node_id = getattr(input_data, "node_id", None)
                    if node_id is not None:
                        res_id = f"node_{node_id}"
                    else:
                        import uuid
                        res_id = str(uuid.uuid4())

                generator = HTMLSlideGenerator()
                html_path = generator.generate(
                    ppt_doc.model_dump(mode="json"),
                    file_id=str(res_id)
                )

                logger.info(
                    "PPT 生成成功",
                    extra={
                        "resource_id": res_id,
                        "slides_count": len(ppt_doc.slides),
                        "theme": ppt_doc.theme_id,
                        "html_path": html_path,
                    },
                )

                return AgentResult(
                    success=True,
                    title=f"{ppt_doc.title} - 教学课件",
                    file_type="html",  # 【修改】从 "pptx" 改为 "html"
                    content="",  # HTML 文件不存储内容在 content 中
                    summary=f"生成 {len(ppt_doc.slides)} 页 HTML 教学课件",
                    metrics={
                        "slide_count": len(ppt_doc.slides),
                    },
                    metadata={
                        "agent_id": "ppt",
                        "slides_count": len(ppt_doc.slides),
                        "theme_id": ppt_doc.theme_id,
                        "template_id": ppt_doc.template_id,
                        "html_file_path": html_path,
                        "html_url": f"/static/html_slides/{res_id}.html",
                        "file_size": os.path.getsize(html_path),
                    },
                    downstream_context=DownstreamContext(
                        source_agent="ppt",
                        title=ppt_doc.title,
                        one_sentence_summary=f"{ppt_doc.title} - {len(ppt_doc.slides)} 页教学课件",
                        reusable_assets=ReusableAssets(examples=[], visual_ideas=[]),
                        covered_outline_ids=[],
                    ),
                )
            except json.JSONDecodeError as e:
                logger.error(f"PPT JSON 解析失败: {e}. Raw content excerpt: {raw_content[:1000]!r}")
                return AgentResult(
                    success=False,
                    title="PPT 生成失败",
                    file_type="json",
                    content=raw_content,
                    error=f"JSON 解析失败: {str(e)}",
                )
            except Exception as e:
                logger.error(f"PPT schema 验证失败: {e}")
                return AgentResult(
                    success=False,
                    title="PPT 生成失败",
                    file_type="json",
                    content=raw_content,
                    error=f"schema 验证失败: {str(e)}",
                )

        except Exception as e:
            logger.error(f"PPT LLM 调用失败: {e}")
            return AgentResult(
                success=False,
                title="PPT 生成失败",
                file_type="json",
                content="",
                error=str(e),
            )
