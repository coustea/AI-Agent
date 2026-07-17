from __future__ import annotations

import re
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.shared.ppt.contract import (
    CourseDomain,
    LogicNodeRole,
    LogicRelation,
    SlideKind,
    VisualFamily,
    select_layout,
    select_provisional_layout,
)
from app.shared.ppt.html import PPTHTMLPublisher, PPTHTMLRenderer, PPTPublication
from app.shared.ppt.models import (
    DeckLogicModel,
    LogicChapter,
    LogicEdge,
    LogicNode,
    PPTArtifact,
    PPTDeck,
    PPTGenerationContext,
    PPTSlide,
    PPTStoryboard,
    PathPPT,
    ResourcePPT,
    SlideBrief,
    SlidePoint,
)
from app.shared.ppt.visual_ir import (
    VisualModel,
    HierarchyVisual,
    GraphVisual,
    StateMachineVisual,
    TimelineVisual,
    MemoryLayoutVisual,
    DataFlowVisual,
    MappingVisual,
    TableMatrixVisual,
    AlgorithmFramesVisual,
    CircuitVisual,
    QuantitativeVisual,
    CodeVisual,
    FormulaVisual,
)
from app.shared.ppt.visual_planner import VisualPlanner
from app.shared.ppt.contract import layout_supports_relation, LayoutKind
from app.infra.llm import get_llm
import asyncio
from pydantic import BaseModel, Field
from typing import Literal, Any

logger = logging.getLogger(__name__)

class SlideBriefPayload(BaseModel):
    kind: SlideKind
    title: str
    teaching_goal: str
    content_focus: str
    chapter_id: str | None = None
    logic_node_ids: list[str] = Field(default_factory=list)
    question: str | None = None
    claim: str | None = None
    bridge: str | None = None
    logic_relation: LogicRelation | None = None
    layout: LayoutKind

class StoryboardPayload(BaseModel):
    title: str
    visual_direction: str
    slides: list[SlideBriefPayload]

class SlideContentPayload(BaseModel):
    lead: str
    points: list[SlidePoint] = Field(default_factory=list)
    speaker_notes: str = ""
    visual_kind: Literal[
        "hierarchy", "graph", "state_machine", "timeline", "memory_layout",
        "data_flow", "mapping", "table_matrix", "algorithm_frames", "circuit",
        "quantitative", "code", "formula"
    ]
    visual_data: dict[str, Any]

VISUAL_MODEL_MAPPING = {
    "hierarchy": HierarchyVisual,
    "graph": GraphVisual,
    "state_machine": StateMachineVisual,
    "timeline": TimelineVisual,
    "memory_layout": MemoryLayoutVisual,
    "data_flow": DataFlowVisual,
    "mapping": MappingVisual,
    "table_matrix": TableMatrixVisual,
    "algorithm_frames": AlgorithmFramesVisual,
    "circuit": CircuitVisual,
    "quantitative": QuantitativeVisual,
    "code": CodeVisual,
    "formula": FormulaVisual,
}

def _validate_slide_visual(payload: SlideContentPayload) -> None:
    import json
    kind = payload.visual_kind
    data = payload.visual_data
    if not isinstance(data, dict):
        raise ValueError("visual_data must be a JSON object")
    
    full_data = {**data, "kind": kind}
    
    model_cls = VISUAL_MODEL_MAPPING.get(kind)
    if not model_cls:
        raise ValueError(f"Unsupported visual kind: {kind}")
        
    try:
        model_cls.model_validate(full_data)
    except Exception as exc:
        err_msg = f"Failed to validate visual_data for {kind} against Pydantic schema.\n"
        err_msg += f"Pydantic Validation Error: {exc}\n"
        err_msg += f"Your invalid visual_data JSON was: {json.dumps(data, ensure_ascii=False, indent=2)}\n"
        err_msg += f"Please make sure it strictly follows the schema rules for {kind}."
        raise ValueError(err_msg)




ProgressCallback = Callable[[str, int], Awaitable[None]]
_PRESENTATION_TIMEZONE = ZoneInfo("Asia/Shanghai")
PPT_PIPELINE_VERSION = "deterministic-html-v6"

# Mapping from logic-node role to a default slide kind and relation when
# synthesising a new slide for an uncovered node during storyboard patching.
_ROLE_KIND_MAP: dict[LogicNodeRole, SlideKind] = {
    LogicNodeRole.QUESTION: SlideKind.QUESTION,
    LogicNodeRole.PREMISE: SlideKind.EXPLANATION,
    LogicNodeRole.CONCEPT: SlideKind.CONCEPT,
    LogicNodeRole.MECHANISM: SlideKind.PROCESS,
    LogicNodeRole.METHOD: SlideKind.PROCESS,
    LogicNodeRole.EVIDENCE: SlideKind.EXPLANATION,
    LogicNodeRole.CASE: SlideKind.COMPARISON,
    LogicNodeRole.CONCLUSION: SlideKind.OBJECTIVE,
}
_ROLE_RELATION_MAP: dict[LogicNodeRole, LogicRelation] = {
    LogicNodeRole.QUESTION: LogicRelation.PREREQUISITE,
    LogicNodeRole.PREMISE: LogicRelation.SUPPORTS,
    LogicNodeRole.CONCEPT: LogicRelation.DECOMPOSES,
    LogicNodeRole.MECHANISM: LogicRelation.CAUSES,
    LogicNodeRole.METHOD: LogicRelation.APPLIES,
    LogicNodeRole.EVIDENCE: LogicRelation.VERIFIES,
    LogicNodeRole.CASE: LogicRelation.CONTRASTS,
    LogicNodeRole.CONCLUSION: LogicRelation.SUMMARIZES,
}
PPT_PIPELINE_STAGES = (
    "assembling_context",
    "designing_logic",
    "designing_story",
    "compiling_visuals",
    "composing_slides",
    "rendering_html",
)
_MAX_SOURCE_MATERIALS = 10
_MARKDOWN_HEADING = re.compile(r"^\s{0,3}(?P<level>#{1,6})\s+(?P<title>.+?)\s*$")
_MARKDOWN_LIST_ITEM = re.compile(r"^\s{0,3}(?:[-*+]\s+|\d+[.)、]\s+)(?P<item>.+?)\s*$")
_SENTENCE_BOUNDARY = re.compile(r"[。！？!?；;]+|\n+")
_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_MARKDOWN_EMPHASIS = re.compile(r"[`*_~]")
_LEADING_LABEL = re.compile(r"^(?P<label>[^：:]{1,12})[：:]\s*(?P<body>.+)$")
_GENERIC_HEADINGS = frozenset(
    {
        "概述",
        "核心概念",
        "概念精解",
        "应用场景",
        "总结",
        "复习建议",
        "高频考点",
        "复习策略",
        "关键解释",
        "案例目标",
    }
)
_NON_FACT_MARKERS = (
    "需要解决什么问题",
    "学习目标",
    "学习路线",
    "能够说明",
    "下一步",
    "形成清晰的学习路径",
)
_DOMAIN_KEYWORDS: dict[CourseDomain, tuple[str, ...]] = {
    CourseDomain.ALGORITHMS: ("算法", "排序", "树", "图", "复杂度", "递归", "动态规划"),
    CourseDomain.OPERATING_SYSTEMS: ("进程", "线程", "死锁", "内存", "调度", "操作系统"),
    CourseDomain.NETWORKS: ("tcp", "udp", "网络", "报文", "握手", "路由", "http"),
    CourseDomain.COMPUTER_ARCHITECTURE: ("cpu", "缓存", "指令", "流水线", "体系结构"),
    CourseDomain.DATABASES: ("数据库", "sql", "事务", "索引", "关系模型"),
    CourseDomain.COMPILERS: ("编译", "词法", "语法", "中间代码", "优化"),
    CourseDomain.DISCRETE_THEORY: ("离散", "集合", "逻辑", "图论", "组合"),
    CourseDomain.SOFTWARE_DISTRIBUTED: ("分布式", "一致性", "微服务", "并发", "系统设计"),
}


@dataclass
class _KnowledgeUnit:
    """One source-grounded teaching unit before it enters the lesson DAG."""

    title: str
    claim: str
    evidence: list[str] = field(default_factory=list)

    def add_evidence(self, fact: str) -> None:
        if fact != self.claim and fact not in self.evidence and len(self.evidence) < 3:
            self.evidence.append(fact)


def ppt_pipeline_metadata() -> dict[str, object]:
    """Expose the actual pipeline contract used by resource and path callers."""

    return {
        "version": PPT_PIPELINE_VERSION,
        "stages": list(PPT_PIPELINE_STAGES),
        "copy_compiler": "deterministic",
    }


class PPTGenerationError(RuntimeError):
    def __init__(self, stage: str, message: str) -> None:
        self.stage = stage
        super().__init__(f"{stage}: {message}")


class PPTContextAdapter:
    """让 resource/path 维持各自参数，仅共享内部生成语义。"""

    @classmethod
    def from_request(cls, request: ResourcePPT | PathPPT) -> PPTGenerationContext:
        if isinstance(request, ResourcePPT):
            # A resource plan is orchestration metadata.  It answers *why* a
            # deck is requested, not *what is true* in the lesson.  Treating
            # it as source material was the direct cause of slides that
            # repeated the learner goal instead of teaching the handoff.
            materials = cls._artifact_materials(request.artifacts)
            return PPTGenerationContext(
                source="resource",
                topic=cls._resource_topic(request),
                learner_profile=cls._profile_text(request.profile),
                learning_goal=cls._text(request.learning_need),
                prerequisites=[],
                source_materials=cls._clean_materials(materials),
                constraints=[f"学习场景：{cls._text(request.learning_scenario)}"],
                preferences=request.preferences,
            )

        # Path metadata is useful for the goal and prerequisite rails, but a
        # lesson's factual source is its authored tutorial body.  Mixing in a
        # summary and bare knowledge-point labels creates title-only slides.
        materials = [request.tutorial_core_content]
        return PPTGenerationContext(
            source="path",
            topic=cls._text(request.node_title),
            learner_profile=cls._profile_text(request.profile),
            learning_goal=cls._text(request.path_goal),
            prerequisites=[cls._text(item) for item in request.knowledge_points[:12]],
            source_materials=cls._clean_materials(materials),
            constraints=[
                f"路径：{cls._text(request.path_title)}",
                f"难度：{cls._text(request.difficulty)}",
                "薄弱点：" + "、".join(cls._text(item) for item in request.weak_knowledge_points[:8]),
            ],
            preferences=request.preferences,
        )

    @classmethod
    def _resource_topic(cls, request: ResourcePPT) -> str:
        """Select the display subject from the structured plan, never the raw need.

        ``learning_need`` describes the learner, their course, and desired
        outcome.  It is deliberately preserved in ``learning_goal``.  A deck
        title instead comes from the planner's scoped subject, with the PPT
        task and upstream artifact headings as progressively less-specific
        sources.  This keeps presentation text and prompt context separate.
        """

        plan = request.resource_plan
        candidates: list[object] = []
        scope = plan.get("scope")
        if isinstance(scope, list):
            candidates.extend(scope)

        tasks = plan.get("tasks")
        if isinstance(tasks, list):
            for task in tasks:
                if not isinstance(task, dict) or task.get("agent_id") != "ppt":
                    continue
                focus = task.get("focus")
                if isinstance(focus, list):
                    candidates.extend(focus)
                candidates.append(task.get("objective", ""))

        candidates.extend(source.title for source in request.artifacts)
        candidates.append(request.learning_need)

        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            title = cls._text(candidate)
            if title:
                return title
        raise ValueError("资源教学计划没有可用的课件主题")

    @staticmethod
    def _profile_text(profile: dict[str, Any] | str) -> str:
        value = profile if isinstance(profile, str) else " ".join(PPTContextAdapter._string_leaves(profile))
        return PPTContextAdapter._text(value)

    @classmethod
    def _artifact_materials(cls, artifacts: list[PPTSource]) -> list[str]:
        """Collect factual handoffs in an order suitable for a lesson compiler.

        The content handoff is prose-first and therefore the strongest source
        for claims.  Code and mind-map handoffs follow as supporting material.
        Titles and one-sentence summaries are deliberately excluded: they are
        labels for another artifact, not evidence for a teaching slide.
        """

        priority = {"content": 0, "code": 1, "mindmap": 2, "quiz": 3, "reading": 4}
        ordered = sorted(
            artifacts,
            key=lambda source: (priority.get(source.agent_id, 9), source.agent_id),
        )
        materials = [
            material
            for source in ordered
            for material in source.materials[:12]
            if material.strip()
        ]
        if not materials:
            raise ValueError("PPT 聚合生成缺少基础 Agent 提供的教学正文")
        return cls._clean_materials(materials)

    @staticmethod
    def _string_leaves(value: object) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            return [item for child in value.values() for item in PPTContextAdapter._string_leaves(child)]
        if isinstance(value, list):
            return [item for child in value for item in PPTContextAdapter._string_leaves(child)]
        return []

    @staticmethod
    def _clean_materials(values: list[str]) -> list[str]:
        """Normalize source material without discarding its factual content.

        The logic compiler and storyboard receive the same source context.
        Every downstream projection receives the same complete facts. Layout
        must adapt at render time rather than silently clipping source truth.
        """
        materials: list[str] = []
        for value in values:
            # Markdown headings and list items encode the author-provided
            # concept boundaries.  Preserve line breaks here; flattening them
            # made the fact compiler lose every heading before it began.
            text = "\n".join(
                " ".join(line.split())
                for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
                if line.strip()
            )
            if not text or len(materials) >= _MAX_SOURCE_MATERIALS:
                continue
            materials.append(text)
        return materials

    @staticmethod
    def _text(value: str) -> str:
        return " ".join(value.split())


class PPTGenerator:
    """Compile source material directly into a self-contained HTML lesson deck.

    The generator intentionally has no language-model dependency. Resource
    planning may use models upstream, but this delivery boundary only accepts
    normalized learning material and deterministically produces a valid deck.
    """

    def __init__(
        self,
        *,
        renderer: PPTHTMLRenderer | None = None,
        planner: VisualPlanner | None = None,
    ) -> None:
        self._renderer = renderer or PPTHTMLRenderer()
        self._planner = planner or VisualPlanner()

    @staticmethod
    def _text(value: str) -> str:
        """Normalize whitespace without applying a presentation text budget."""

        return " ".join(value.split())

    async def generate(
        self,
        request: ResourcePPT | PathPPT,
        *,
        output_dir: Path,
        progress: ProgressCallback | None = None,
    ) -> PPTArtifact:
        stage = "assembling_context"
        try:
            context = PPTContextAdapter.from_request(request)
            await self._progress(progress, "正在整理课程材料…", 8)

            stage = "designing_logic"
            await self._progress(progress, "教学逻辑架构师正在建立知识依赖模型…", 20)
            logic_model = await self._generate_logic_model_llm(context)

            stage = "designing_story"
            await self._progress(progress, "正在将知识链编译为教学故事板…", 34)
            storyboard = await self._compile_storyboard_llm(context, logic_model)
            self._validate_storyboard_logic(storyboard, logic_model)

            stage = "compiling_visuals"
            await self._progress(progress, "正在设计每页幻灯片的图解和排版…", 48)

            stage = "composing_slides"
            await self._progress(progress, "正在并行生成每一页课件的详细内容与深度图解…", 60)
            deck = await self._compose_deck_llm(context, logic_model, storyboard)

            stage = "rendering_html"
            await self._progress(progress, "正在将语义版式渲染为 HTML/SVG 课件…", 88)
            publication = PPTPublication(generated_at=datetime.now(_PRESENTATION_TIMEZONE))
            document = self._renderer.render(deck, publication)

            stage = "publishing"
            path = PPTHTMLPublisher(output_dir).publish("slides", document)
            await self._progress(progress, "课件生成完成", 100)
        except PPTGenerationError:
            raise
        except Exception as exc:
            raise PPTGenerationError(stage, str(exc)) from exc

        return PPTArtifact(
            title=deck.title,
            path=path,
            generated_at=publication.generated_at,
            slide_count=len(deck.slides),
        )

    async def _generate_logic_model_llm(self, context: PPTGenerationContext) -> DeckLogicModel:
        llm = get_llm()
        
        materials_text = ""
        for i, mat in enumerate(context.source_materials, 1):
            materials_text += f"--- 材料段落 {i} ---\n{mat}\n\n"
            
        prereqs_text = "、".join(context.prerequisites) if context.prerequisites else "无"
        constraints_text = "\n".join(f"- {c}" for c in context.constraints) if context.constraints else "无"
        emphasis_text = "、".join(context.preferences.emphasis) if context.preferences.emphasis else "无"
        
        prompt = f"""你是一个顶级的计算机科学教育专家与课程设计师。
请根据以下输入，为课程主题“{context.topic}”设计一个严格、连通且无环的教学逻辑图模型（DeckLogicModel）。

【课程基本信息】
- 主题：{context.topic}
- 学习目标：{context.learning_goal}
- 学员画像：{context.learner_profile or '标准学员'}
- 前置知识：{prereqs_text}
- 偏好设定：叙事风格={context.preferences.narrative_style}，内容密度={context.preferences.density}，教学重点={emphasis_text}
- 额外约束：
{constraints_text}

【可用的基础材料】
{materials_text}

【设计与验证规则 - 极其重要】
1. 课程领域 `course_domain`：请在以下值中选择最契合的一个：'algorithms', 'operating_systems', 'networks', 'computer_architecture', 'databases', 'compilers', 'discrete_theory', 'software_distributed', 'general_cs'。
2. 核心问题 `central_question`：本课程的核心疑问（例如：“如何利用栈的后进先出特性解决括号匹配问题？”），字数控制在 40 字内。
3. 核心主张 `thesis`：本课程想传达的最终学术主张/结论（例如：“栈通过限定一端操作确保后进先出，是函数调用和语法解析的物理基础。”），控制在 80 字内。
4. 教学章节 `chapters`：对于 10 页左右的精简课件，**必须且仅能规划 2 个章节**：
   - 第一章（ID 为 `c01`）：侧重于概念与结构，标题如“概念与结构”、“基础与表示”等。
   - 第二章（ID 为 `c02`）：侧重于方法与应用，标题如“机制与操作”、“算法与应用”等。
   - 每个章节必须有核心问题（`question`）、最终输出结论（`outcome`），以及包含的逻辑节点 ID 列表（`node_ids`）。
5. 逻辑节点 `nodes`：根据材料，设计 4 到 8 个核心知识节点。
   - 节点 ID 必须按顺序为 `l01`, `l02`, `l03`...。
   - 每个节点**必须**包含 `chapter_id` 字段，值为该节点所属章节的 ID（`c01` 或 `c02`），确保所有节点被 chapters 覆盖且仅覆盖一次。
   - 角色 `role` 必须属于：'question', 'premise', 'concept', 'mechanism', 'method', 'evidence', 'case', 'conclusion'。
   - 每个节点**必须**包含简短标题 `title`（2-20字，概括节点核心概念）和核心问题 `question`（该节点要回答的关键问题，10-40字）。
   - 每个节点必须设定学术性的核心结论 `claim`，并且必须包含 1-3 个具体的非空支持论据 `evidence`（在 evidence 列表中，绝对不能留空或全为空白字符）。
   - 每个节点必须包含最终输出结论 `output`（10-60字，该节点推导出的可复用结论）。
6. 逻辑关系边 `edges`：用有向边连接逻辑节点，描述它们之间的递进关系。
   - 必须构成一个**单一的、连通的、无环的有向图（DAG）**。不能有孤立节点，也不能有环。
   - 每条边包含 `source_id`、`target_id`。
   - 关系类型 `relation` 必须是：'prerequisite', 'decomposes', 'supports', 'derives', 'causes', 'contrasts', 'applies', 'verifies', 'summarizes'。
   - 过渡桥梁 `bridge` 说明为什么从 source 到 target 推进（例如：“在掌握了顺序栈的物理表示后，接下来分析其关键操作入栈的代码实现。”），控制在 60 字内。

请输出符合 DeckLogicModel 结构的 JSON 对象。"""
        
        return await llm.ainvoke_json(DeckLogicModel, prompt)

    async def _compile_storyboard_llm(
        self,
        context: PPTGenerationContext,
        logic_model: DeckLogicModel,
    ) -> PPTStoryboard:
        llm = get_llm()
        
        logic_summary = f"中心问题：{logic_model.central_question}\n核心结论：{logic_model.thesis}\n"
        logic_summary += "章节与节点结构：\n"
        for i, chapter in enumerate(logic_model.chapters, 1):
            logic_summary += f"章节 {chapter.id}: {chapter.title} (问题: {chapter.question})\n"
            for node_id in chapter.node_ids:
                node = next(n for n in logic_model.nodes if n.id == node_id)
                logic_summary += f"  - 节点 {node.id}: {node.title} (角色: {node.role.value}, 结论: {node.claim})\n"
                
        prompt = f"""你是一个顶级的高端多媒体教学编剧。
请根据以下教学逻辑模型，为课程主题“{context.topic}”编译一份精致的幻灯片故事板（PPTStoryboard）。

【当前课程的教学逻辑模型】
{logic_summary}

【故事板设计与校验规则 - 极其重要】
1. 幻灯片页面列表 `slides` 总数必须在 7 到 18 页之间。
2. 幻灯片 ID 必须依次为 `s01`, `s02`, `s03`...。
3. 故事板必须符合严格的经典教学弧线：
   - 第一页必须是封面（`kind` 为 'cover'，ID 为 `s01`），`layout` 为 'hero'。
   - 第二页必须是学习路线（`kind` 为 'roadmap'，ID 为 `s02`），`layout` 为 'route'。
   - 中间为内容幻灯片，必须按照逻辑章节的顺序连续排布（例如，c01 章节的所有幻灯片在前面，c02 章节的所有幻灯片紧随其后，绝对不能交错）。
   - 最后一页必须是课程总结（`kind` 为 'summary'），`layout` 为 'recap'。
4. 对于内容幻灯片：
   - `kind` 必须是：'question', 'concept', 'process', 'explanation', 'comparison', 'correction', 'map', 'objective'。
   - 必须指明所属章节 `chapter_id`（'c01' 或 'c02'）。
   - 必须关联 1 到 5 个逻辑节点 `logic_node_ids`。内容页必须完整覆盖 logic_model 中的所有节点。
   - 必须指定它的主导逻辑关系 `logic_relation`（'prerequisite', 'decomposes', 'supports', 'derives', 'causes', 'contrasts', 'applies', 'verifies', 'summarizes'）。
   - 必须指定其版式 `layout`。版式必须与 `logic_relation` 严格契合：
     * `prerequisite` -> 支持 'diagram', 'sequence', 'statement'
     * `decomposes` -> 支持 'diagram', 'mosaic', 'recap'
     * `supports` -> 支持 'statement', 'diagram', 'mosaic'
     * `derives` -> 支持 'sequence', 'studio'
     * `causes` -> 支持 'sequence', 'diagram'
     * `contrasts` -> 支持 'comparison'
     * `applies` -> 支持 'studio', 'diagram', 'mosaic'
     * `verifies` -> 支持 'studio', 'statement', 'mosaic'
     * `summarizes` -> 支持 'recap', 'diagram'
   - `title`：页面的主标题，控制在 15 字以内，要精准、抓人。
   - `teaching_goal`：设定本页的具体教学意图或认知目标。
   - `content_focus`：本页面的教学点或知识细节聚焦。
   - `question`、`claim`、`bridge`：根据关联的逻辑节点填入对应的核心问答与逻辑过渡桥梁。

请输出符合 StoryboardPayload 结构的 JSON 对象。"""

        payload: StoryboardPayload = await llm.ainvoke_json(StoryboardPayload, prompt)
        
        slides: list[SlideBrief] = []
        for index, item in enumerate(payload.slides, start=1):
            slide_id = f"s{index:02d}"
            layout = item.layout
            
            # Correct layout mismatch
            if item.kind not in {SlideKind.COVER, SlideKind.ROADMAP, SlideKind.SUMMARY}:
                relation = item.logic_relation or LogicRelation.SUPPORTS
                if not layout_supports_relation(layout, relation):
                    layout = select_provisional_layout(item.kind, relation)
                
                # Auto-fill missing fields from associated logic nodes to guarantee validation stability
                question = (item.question or "").strip()
                claim = (item.claim or "").strip()
                bridge = (item.bridge or "").strip()
                chapter_id = item.chapter_id
                
                nodes_by_id = {node.id: node for node in logic_model.nodes}
                if item.logic_node_ids:
                    first_node = nodes_by_id.get(item.logic_node_ids[0])
                    if first_node:
                        if not question:
                            question = first_node.question
                        if not claim:
                            claim = first_node.claim
                        if not chapter_id:
                            chapter_id = first_node.chapter_id
                            
                if not question:
                    question = "如何理解本页的核心教学点？"
                if not claim:
                    claim = item.title
                if not bridge:
                    bridge = "下面继续探讨核心知识点的逻辑关系。"
                if not chapter_id:
                    chapter_id = "c01"
            else:
                if item.kind == SlideKind.COVER:
                    layout = LayoutKind.HERO
                elif item.kind == SlideKind.ROADMAP:
                    layout = LayoutKind.ROUTE
                elif item.kind == SlideKind.SUMMARY:
                    layout = LayoutKind.RECAP
                question = item.question or ""
                claim = item.claim or ""
                bridge = item.bridge or ""
                chapter_id = item.chapter_id

            slides.append(
                SlideBrief(
                    id=slide_id,
                    kind=item.kind,
                    title=item.title,
                    teaching_goal=item.teaching_goal,
                    content_focus=item.content_focus,
                    chapter_id=chapter_id,
                    logic_node_ids=item.logic_node_ids,
                    question=question,
                    claim=claim,
                    bridge=bridge,
                    logic_relation=item.logic_relation,
                    layout=layout,
                    density=context.preferences.density,
                )
            )
            
        # --- Deterministic patch: ensure every logic node is covered ---
        slides = self._patch_uncovered_nodes(slides, logic_model)

        return PPTStoryboard(
            title=payload.title,
            visual_direction=payload.visual_direction,
            slides=slides,
        )

    async def _compose_deck_llm(
        self,
        context: PPTGenerationContext,
        logic_model: DeckLogicModel,
        storyboard: PPTStoryboard,
    ) -> PPTDeck:
        tasks = []
        for brief in storyboard.slides:
            if brief.kind in {SlideKind.COVER, SlideKind.ROADMAP, SlideKind.SUMMARY}:
                continue
            tasks.append(self._compose_content_slide_llm(context, logic_model, storyboard, brief))
            
        content_slides = await asyncio.gather(*tasks)
        content_slides_by_id = {slide.id: slide for slide in content_slides}
        
        slides = []
        for brief in storyboard.slides:
            if brief.kind in {SlideKind.COVER, SlideKind.ROADMAP, SlideKind.SUMMARY}:
                lead, points, notes = self._compose_copy(brief, logic_model, context)
                slide = PPTSlide(
                    id=brief.id,
                    kind=brief.kind,
                    title=brief.title,
                    chapter_id=brief.chapter_id,
                    logic_node_ids=brief.logic_node_ids,
                    question=brief.question,
                    claim=brief.claim,
                    bridge=brief.bridge,
                    logic_relation=brief.logic_relation,
                    layout=brief.layout,
                    density=brief.density,
                    visual=None,
                    lead=lead,
                    points=points,
                    speaker_notes=notes,
                )
            else:
                slide = content_slides_by_id[brief.id]
            slides.append(slide)
            
        return PPTDeck(
            title=storyboard.title,
            language=storyboard.language,
            visual_direction=storyboard.visual_direction,
            logic_model=logic_model,
            slides=slides,
        )

    async def _compose_content_slide_llm(
        self,
        context: PPTGenerationContext,
        logic_model: DeckLogicModel,
        storyboard: PPTStoryboard,
        brief: SlideBrief,
    ) -> PPTSlide:
        llm = get_llm()
        
        # Build storyboard overview for contextual continuity and preventing repetitions
        storyboard_overview = ""
        for slide_brief in storyboard.slides:
            marker = " <--- 当前正在设计并撰写此页内容" if slide_brief.id == brief.id else ""
            storyboard_overview += f"- 页面 {slide_brief.id} (类型: {slide_brief.kind.value}): {slide_brief.title}{marker}\n"
            
        nodes_by_id = {node.id: node for node in logic_model.nodes}
        associated_nodes = [nodes_by_id[nid] for nid in brief.logic_node_ids]
        node_details = ""
        for node in associated_nodes:
            node_details += f"--- 知识节点 {node.id} ({node.title}) ---\n"
            node_details += f"核心结论 (claim): {node.claim}\n"
            node_details += "论据 (evidence):\n"
            for ev in node.evidence:
                node_details += f"  - {ev}\n"
            node_details += f"最终产出 (output): {node.output}\n\n"
            
        prompt = f"""你是一个高级的计算机科学教学板面和视觉图解设计师。
请为以下标有 `<---` 的幻灯片页面设计其详细的内容文案，并提供最符合该页教学点和语义的图解（Visual IR）。

【整个 PPT 故事板大纲】
{storyboard_overview}

【当前幻灯片基本信息】
- 页面 ID：{brief.id}
- 类型：{brief.kind.value}
- 标题：{brief.title}
- 教学目标：{brief.teaching_goal}
- 内容重心：{brief.content_focus}
- 逻辑关系：{brief.logic_relation.value if brief.logic_relation else '无'}
- 推荐版式：{brief.layout.value}

【关联的教学逻辑节点信息】
{node_details}

【设计与验证规则 - 极其重要】
1. 页面核心结论 `lead`：主导画面的核心一句话，必须有学术深度且精练，不超过 80 字。
2. 页面要点 `points`：包含 1 到 3 个支撑要点。
   - 每个要点包含标签 `label` 和说明 `detail`。
   - 标签 `label` 必须极其精炼且具有场景特异性（如 '操作步骤'、'边界处理'、'物理结构'、'性能特征'等，禁止使用无意义的通用标签如'补充事实'、'应用提示'）。
   - 说明 `detail` 展开叙述该教学点。
3. 讲稿旁白 `speaker_notes`：口语化的讲稿，指导讲师如何展开技术细节、提示授课重点，控制在 150 字以内。
4. 图解类型 `visual_kind` 与图解数据 `visual_data`：
   - 从以下列表中选择最契合当前页面内容的 `visual_kind`，并在 `visual_data` 中填写其对应的字段。
   - **绝对不能提供与类型不相符的字段**，所有索引编号必须从 0 开始且在合法范围内。

【可用的 Visual IR 列表与字段格式说明】
- 'code'：代码块。格式：
  {{
    "language": "cpp",  // cpp, python, etc.
    "lines": ["line 1", "line 2", ...],  // 4 到 18 行代码
    "highlighted_line_indices": [1, 3]  // 0-indexed 行号列表，可以为空
  }}
- 'algorithm_frames'：算法/执行步骤序列帧。格式：
  {{
    "frames": [
      {{ "title": "步骤1", "cells": ["元素A", "元素B"], "highlighted_cell_indices": [0] }},
      ...
    ]  // 2 到 8 个 frame
  }}
- 'memory_layout'：内存布局。格式：
  {{
    "segments": [
      {{ "label": "栈顶", "size": 4.0 }},
      {{ "label": "栈底", "size": 8.0 }}
    ],  // size 必须大于 0
    "references": [
      {{ "source_segment_index": 0, "target_segment_index": 1, "relation": "pointer", "label": "指向" }}
    ]  // references 可以为空
  }}
- 'table_matrix'：表格矩阵。格式：
  {{
    "headers": ["表头1", "表头2"],
    "rows": [
      {{ "cells": ["单元格1", "单元格2"] }}
    ],  // cells 数量必须与 headers 一致
    "highlighted_row_indices": [0],
    "highlighted_column_indices": [1]
  }}
- 'state_machine'：状态机图解。格式：
  {{
    "states": [
      {{ "label": "空栈", "initial": true, "final": false }},
      {{ "label": "满栈", "initial": false, "final": true }}
    ],  // 必须且仅有一个 initial 为 true 的状态
    "transitions": [
      {{ "source_index": 0, "target_index": 1, "label": "入栈直到满" }}
    ]
  }}
- 'graph'：节点关系图。格式：
  {{
    "directed": true,
    "nodes": [
      {{ "label": "节点A" }},
      {{ "label": "节点B" }}
    ],
    "edges": [
      {{ "source_index": 0, "target_index": 1, "label": "依赖" }}
    ]
  }}
- 'hierarchy'：层级树图。格式：
  {{
    "nodes": [
      {{ "label": "根节点", "parent_index": null }},
      {{ "label": "子节点1", "parent_index": 0 }}
    ]  // 必须有且仅有一个 parent_index 为 null 的根节点，必须连通无环
  }}
- 'timeline'：时序步骤。格式：
  {{
    "lanes": [{{ "label": "发送方" }}, {{ "label": "接收方" }}],
    "events": [
      {{ "lane_index": 0, "start": 0.0, "end": 1.5, "label": "打包数据" }}
    ],  // start 必须小于 end
    "messages": [
      {{ "source_lane_index": 0, "target_lane_index": 1, "at": 1.5, "label": "发送请求" }}
    ]
  }}
- 'mapping'：映射对比。格式：
  {{
    "mode": "relation",  // relation 或 function
    "left_set_label": "输入",
    "right_set_label": "输出",
    "left_elements": ["A"],
    "right_elements": ["B"],
    "pairs": [{{ "source_index": 0, "target_index": 0 }}]
  }}
- 'quantitative'：定量图表。格式：
  {{
    "x_axis": {{ "label": "规模", "unit": "N" }},
    "y_axis": {{ "label": "耗时", "unit": "ms" }},
    "series": [
      {{
        "label": "算法A",
        "points": [{{ "x_value": 10, "y_value": 5.0 }}]
      }}
    ]
  }}
- 'formula'：公式推导。格式：
  {{
    "expression": "f(n) = O(g(n))",
    "steps": [
      {{ "expression": "第一步", "explanation": "说明" }}
    ],
    "variables": [
      {{ "symbol": "n", "meaning": "输入规模" }}
    ]
  }}

请输出符合 SlideContentPayload 结构的 JSON 对象。"""

        payload: SlideContentPayload = await llm.ainvoke_json(
            SlideContentPayload,
            prompt,
            validator=_validate_slide_visual,
        )
        
        kind = payload.visual_kind
        full_data = {**payload.visual_data, "kind": kind}
        visual_model = VISUAL_MODEL_MAPPING[kind].model_validate(full_data)
        
        layout = select_layout(
            brief.kind,
            VisualFamily(kind),
            brief.logic_relation,
        )
        
        return PPTSlide(
            id=brief.id,
            kind=brief.kind,
            title=brief.title,
            chapter_id=brief.chapter_id,
            logic_node_ids=brief.logic_node_ids,
            question=brief.question,
            claim=brief.claim,
            bridge=brief.bridge,
            logic_relation=brief.logic_relation,
            layout=layout,
            density=brief.density,
            visual=visual_model,
            lead=payload.lead,
            points=payload.points,
            speaker_notes=payload.speaker_notes,
        )



    _NARRATIVE_CHAPTER_TITLES: dict[str, tuple[str, str]] = {
        "concept": ("概念与结构", "方法与应用"),
        "case_driven": ("案例引入", "实践与迁移"),
        "problem_led": ("问题与线索", "推导与解决"),
        "review": ("核心回顾", "查漏与巩固"),
    }

    _NARRATIVE_QUESTIONS: dict[str, str] = {
        "concept": "如何理解并应用{topic}？",
        "case_driven": "{topic}在真实场景中如何发挥作用？",
        "problem_led": "关于{topic}的核心问题是什么？如何解决？",
        "review": "{topic}有哪些必须掌握的要点和常见误区？",
    }

    _EMPHASIS_ROLE_BOOST: dict[str, list[LogicNodeRole]] = {
        "core_concepts": [LogicNodeRole.CONCEPT, LogicNodeRole.MECHANISM],
        "cases": [LogicNodeRole.CASE, LogicNodeRole.EVIDENCE],
        "pitfalls": [LogicNodeRole.CONCLUSION],
        "derivation": [LogicNodeRole.METHOD, LogicNodeRole.MECHANISM],
    }

    @classmethod
    def _generate_logic_model(cls, context: PPTGenerationContext) -> DeckLogicModel:
        """Build a bounded teaching graph from human-readable source material."""

        units = cls._knowledge_units(context)
        chapter_break = max(2, min(3, len(units) // 2))
        narrative = context.preferences.narrative_style
        emphasis = set(context.preferences.emphasis)
        nodes: list[LogicNode] = []
        for index, unit in enumerate(units, start=1):
            role = cls._role_for_unit(unit, emphasis_boost=emphasis)
            chapter_id = "c01" if index <= chapter_break else "c02"
            nodes.append(
                LogicNode(
                    id=f"l{index:02d}",
                    chapter_id=chapter_id,
                    title=cls._text(unit.title),
                    role=role,
                    question=cls._question_for(unit.title, role),
                    claim=cls._text(unit.claim),
                    # The graph contract requires evidence for every node.  A
                    # standalone source fact is its own evidence; downstream
                    # copy/visual projections de-duplicate it before display.
                    evidence=[
                        cls._text(item)
                        for item in (unit.evidence or [unit.claim])
                    ],
                    output=cls._output_for(unit),
                )
            )

        c1_title, c2_title = cls._NARRATIVE_CHAPTER_TITLES.get(narrative, ("概念与结构", "方法与应用"))
        chapters: list[LogicChapter] = []
        for chapter_id, title, chapter_nodes in (
            ("c01", c1_title, [node for node in nodes if node.chapter_id == "c01"]),
            ("c02", c2_title, [node for node in nodes if node.chapter_id == "c02"]),
        ):
            if not chapter_nodes:
                continue
            chapters.append(
                LogicChapter(
                    id=chapter_id,
                    title=title,
                    question=chapter_nodes[0].question,
                    outcome=chapter_nodes[-1].output,
                    node_ids=[node.id for node in chapter_nodes],
                )
            )

        return DeckLogicModel(
            course_domain=cls._infer_course_domain(context),
            central_question=cls._text(cls._NARRATIVE_QUESTIONS.get(narrative, "如何理解并应用{topic}？").format(topic=context.topic)),
            thesis=cls._text("；".join(node.claim for node in nodes[-2:])),
            chapters=chapters,
            nodes=nodes,
            edges=[
                LogicEdge(
                    source_id=source.id,
                    target_id=target.id,
                    relation=cls._relation_for(target),
                    bridge=cls._bridge_for(source, target),
                )
                for source, target in zip(nodes, nodes[1:])
            ],
        )

    @classmethod
    def _knowledge_units(cls, context: PPTGenerationContext) -> list[_KnowledgeUnit]:
        """Compile headings and facts from handoffs, never from task metadata.

        A source heading owns the facts beneath it.  This preserves the
        author's concept boundaries (for example ``前序遍历``) instead of
        turning every sentence or user request into a slide title.
        """

        by_title: dict[str, _KnowledgeUnit] = {}
        seen_facts: set[str] = set()
        for material in context.source_materials:
            active_title = ""
            in_code_fence = False
            for raw_line in material.splitlines():
                line = raw_line.strip()
                if line.startswith("```"):
                    in_code_fence = not in_code_fence
                    continue
                if not line or in_code_fence:
                    continue

                heading = _MARKDOWN_HEADING.match(line)
                if heading:
                    candidate = cls._clean_source_text(heading.group("title"))
                    active_title = "" if candidate in _GENERIC_HEADINGS else candidate
                    continue

                item = _MARKDOWN_LIST_ITEM.match(line)
                if item:
                    line = item.group("item")
                line = cls._clean_source_text(line)
                if not line:
                    continue

                title_from_line, fact_line = cls._line_semantics(line)
                for fact in cls._sentences(fact_line):
                    if not cls._is_teaching_fact(fact):
                        continue
                    title = title_from_line or active_title or cls._unit_title(fact, context.topic)
                    title = cls._text(title)
                    normalized = cls._normalize_fact(fact)
                    if not title or not normalized or normalized in seen_facts:
                        continue
                    seen_facts.add(normalized)
                    unit = by_title.get(title)
                    if unit is None:
                        by_title[title] = _KnowledgeUnit(
                            title=title,
                            claim=fact,
                            evidence=cls._sequence_steps(fact),
                        )
                    else:
                        unit.add_evidence(fact)

        units = list(by_title.values())
        if len(units) < 4:
            raise PPTGenerationError(
                "designing_logic",
                "基础资源缺少足够的知识事实，无法生成教学课件；请确保至少提供 4 个含定义、步骤或案例的内容单元",
            )
        return units[:8]

    @staticmethod
    def _clean_source_text(value: str) -> str:
        plain = _MARKDOWN_LINK.sub(r"\1", value)
        plain = _MARKDOWN_EMPHASIS.sub("", plain)
        return " ".join(plain.split()).strip("：:，,。；;！!？? ")

    @classmethod
    def _line_semantics(cls, line: str) -> tuple[str, str]:
        """Split a labelled source line into a concept title and its fact."""

        match = _LEADING_LABEL.match(line)
        if not match:
            return "", line
        label = cls._clean_source_text(match.group("label"))
        body = cls._clean_source_text(match.group("body"))
        if label in {"定义", "作用", "特点", "说明", "步骤", "结论", "注意", "类比", "访问顺序"}:
            return "", body
        return label, body

    @classmethod
    def _sentences(cls, value: str) -> list[str]:
        return [
            cls._clean_source_text(part)
            for part in _SENTENCE_BOUNDARY.split(value)
            if len(cls._clean_source_text(part)) >= 2
        ]

    @staticmethod
    def _normalize_fact(value: str) -> str:
        return re.sub(r"[\s，,。；;：:！!？?]", "", value).lower()

    @classmethod
    def _is_teaching_fact(cls, value: str) -> bool:
        if len(value) < 2 or value.endswith(("？", "?")):
            return False
        return not any(marker in value for marker in _NON_FACT_MARKERS)

    @staticmethod
    def _sequence_steps(value: str) -> list[str]:
        """Extract explicit ordered steps without inventing a process."""

        matches = re.findall(r"(先|再|然后|最后)([^，,。；;]+)", value)
        steps = [f"{prefix}{body.strip()}" for prefix, body in matches if body.strip()]
        return list(dict.fromkeys(steps))[:3] if len(steps) >= 2 else []

    @classmethod
    def _unit_title(cls, value: str, fallback: str) -> str:
        text = " ".join(value.split()).strip("：:，,。；;！!？? ")
        if "：" in text:
            text = text.split("：", 1)[0]
        for token in ("是", "指", "通过", "包括", "用于"):
            if token in text:
                candidate = text.split(token, 1)[0].strip("的 ，。；：、 -—")
                if len(candidate) >= 2:
                    text = candidate
                    break
        return text if len(text) >= 2 else cls._text(fallback)

    @classmethod
    def _infer_course_domain(cls, context: PPTGenerationContext) -> CourseDomain:
        corpus = " ".join((context.topic, context.learning_goal, *context.source_materials)).lower()
        for domain, keywords in _DOMAIN_KEYWORDS.items():
            if any(keyword in corpus for keyword in keywords):
                return domain
        return CourseDomain.GENERAL_CS

    @classmethod
    def _role_for_unit(cls, unit: _KnowledgeUnit, *, emphasis_boost: set[str] | None = None) -> LogicNodeRole:
        corpus = f"{unit.title} {' '.join([unit.claim, *unit.evidence])}"
        # When emphasis includes pitfalls, boost conclusion detection
        boost_roles: set[LogicNodeRole] = set()
        if emphasis_boost:
            for emphasis_key in emphasis_boost:
                boost_roles.update(cls._EMPHASIS_ROLE_BOOST.get(emphasis_key, []))
        if any(token in corpus for token in ("对比", "区别", "差异", "联系")):
            return LogicNodeRole.CASE
        if any(token in corpus for token in ("步骤", "顺序", "遍历", "流程", "算法")):
            return LogicNodeRole.METHOD
        if any(token in corpus for token in ("机制", "原理", "结构", "线索", "指针")):
            return LogicNodeRole.MECHANISM
        if any(token in corpus for token in ("误区", "注意", "结论", "总结")):
            return LogicNodeRole.CONCLUSION
        # No keyword match — prefer a role that aligns with emphasis
        if boost_roles:
            return next(iter(boost_roles))
        return LogicNodeRole.CONCEPT

    @classmethod
    def _question_for(cls, title: str, role: LogicNodeRole) -> str:
        if role is LogicNodeRole.METHOD:
            return cls._text(f"如何正确执行{title}？")
        if role is LogicNodeRole.CASE:
            return cls._text(f"{title}之间有什么差异或联系？")
        if role is LogicNodeRole.MECHANISM:
            return cls._text(f"{title}为什么能发挥作用？")
        return cls._text(f"{title}的关键特征是什么？")

    @classmethod
    def _output_for(cls, unit: _KnowledgeUnit) -> str:
        evidence = "；".join(unit.evidence[:2])
        if evidence:
            return cls._text(f"结合{evidence}理解{unit.title}。")
        return cls._text(f"依据“{unit.claim}”理解{unit.title}。")

    @classmethod
    def _relation_for(cls, target: LogicNode) -> LogicRelation:
        """Choose a visual relation from available source structure.

        A node with one factual statement is evidence, not a fabricated flow.
        More specialised diagrams are reserved for source text that explicitly
        carries a sequence or comparison relation.
        """

        corpus = " ".join((target.title, target.claim, *target.evidence))
        if target.role is LogicNodeRole.CASE and any(
            token in corpus for token in ("对比", "区别", "差异", "联系")
        ):
            return LogicRelation.CONTRASTS
        if target.role is LogicNodeRole.METHOD and any(
            token in corpus for token in ("先", "再", "然后", "最后", "步骤", "顺序")
        ):
            return LogicRelation.DERIVES
        return LogicRelation.SUPPORTS

    @staticmethod
    def _bridge_for(source: LogicNode, target: LogicNode) -> str:
        return f"从{source.title}出发，继续理解{target.title}。"[:96]

    @staticmethod
    def _compile_storyboard(
        context: PPTGenerationContext,
        logic_model: DeckLogicModel,
    ) -> PPTStoryboard:
        """Compile a teaching DAG into the canonical cover-to-summary arc.

        The storyboard owns teaching sequence and provisional composition only.
        It deliberately makes no visual-family decision; the visual planner
        resolves that independent concern after this compiler has finished.

        Args:
            context: Normalized lesson request and copy preferences.
            logic_model: Validated teaching graph with canonical node identity.

        Returns:
            A seven-to-eighteen-slide storyboard covering every logic node.

        Raises:
            PPTGenerationError: If nodes cannot be grouped without crossing a
                chapter or exceeding the slide budget.
        """

        chapters_by_id = {chapter.id: chapter for chapter in logic_model.chapters}
        nodes_by_id = {node.id: node for node in logic_model.nodes}

        def relation_for(node_ids: list[str]) -> LogicEdge:
            primary_id = node_ids[0]
            for edge in logic_model.edges:
                if edge.target_id == primary_id:
                    return edge
            # The first knowledge node has no incoming edge.  It is presented
            # as a source-backed fact, not as a fabricated prerequisite flow.
            primary = nodes_by_id[primary_id]
            return LogicEdge(
                source_id=primary.id,
                target_id=logic_model.nodes[1].id,
                relation=LogicRelation.SUPPORTS,
                bridge="从第一个知识事实开始建立课程框架。",
            )

        def content_brief(
            *,
            kind: SlideKind,
            title: str,
            teaching_goal: str,
            content_focus: str,
            node_ids: list[str],
        ) -> SlideBrief:
            primary = nodes_by_id[node_ids[0]]
            chapter = chapters_by_id[primary.chapter_id]
            if any(nodes_by_id[node_id].chapter_id != chapter.id for node_id in node_ids):
                raise PPTGenerationError("designing_story", "一页知识内容不能跨章节合并")
            relation = relation_for(node_ids)
            return SlideBrief(
                id="s00",
                kind=kind,
                title=title[:54],
                teaching_goal=teaching_goal[:150],
                content_focus=content_focus[:180],
                chapter_id=chapter.id,
                logic_node_ids=node_ids,
                question=primary.question,
                claim=primary.claim,
                bridge=relation.bridge,
                logic_relation=relation.relation,
                layout=select_provisional_layout(kind, relation.relation),
                density=context.preferences.density,
            )

        groups: list[tuple[str, list[str]]] = [
            (chapter.id, [node_id])
            for chapter in logic_model.chapters
            for node_id in chapter.node_ids
        ]
        while len(groups) > 15:
            merge_at = next(
                (
                    index
                    for index in range(len(groups) - 1)
                    if (
                        groups[index][0] == groups[index + 1][0]
                        and len(groups[index][1]) + len(groups[index + 1][1]) <= 3
                    )
                ),
                None,
            )
            if merge_at is None:
                raise PPTGenerationError("designing_story", "知识章节无法在 18 页内连续编排")
            chapter_id, node_ids = groups[merge_at]
            groups[merge_at] = (chapter_id, node_ids + groups[merge_at + 1][1])
            del groups[merge_at + 1]

        briefs: list[SlideBrief] = [
            SlideBrief(
                id="s00",
                kind=SlideKind.COVER,
                title=context.topic,
                teaching_goal=logic_model.thesis,
                content_focus=logic_model.central_question,
                layout=select_provisional_layout(SlideKind.COVER, None),
                density=context.preferences.density,
            ),
            SlideBrief(
                id="s00",
                kind=SlideKind.ROADMAP,
                title="学习路线",
                teaching_goal="建立从问题到应用的完整学习路径",
                content_focus=" → ".join(chapter.title for chapter in logic_model.chapters)[:180],
                layout=select_provisional_layout(SlideKind.ROADMAP, None),
                density=context.preferences.density,
            ),
        ]

        for _chapter_id, node_ids in groups:
            primary = nodes_by_id[node_ids[0]]
            kind = PPTGenerator._slide_kind_for_role(primary.role)
            focus = primary.claim
            if len(node_ids) > 1:
                focus = "；".join(nodes_by_id[node_id].claim for node_id in node_ids)
            briefs.append(
                content_brief(
                    kind=kind,
                    title=primary.title,
                    teaching_goal=primary.output,
                    content_focus=focus,
                    node_ids=node_ids,
                )
            )

        briefs.append(
            SlideBrief(
                id="s00",
                kind=SlideKind.SUMMARY,
                title="课程总结",
                teaching_goal="回收核心问题并形成后续学习行动",
                content_focus=logic_model.central_question,
                layout=select_provisional_layout(SlideKind.SUMMARY, None),
                density=context.preferences.density,
            )
        )

        numbered = [
            brief.model_copy(update={"id": f"s{index:02d}"})
            for index, brief in enumerate(briefs, start=1)
        ]
        return PPTStoryboard(
            title=context.topic,
            visual_direction="现代教学课件：以关系模型、过程演示和关键对比组织信息，图解优先且适合课堂放映。",
            slides=numbered,
        )

    @staticmethod
    def _slide_kind_for_role(role: LogicNodeRole) -> SlideKind:
        """Map a teaching role to copy semantics without choosing visuals."""

        return {
            LogicNodeRole.QUESTION: SlideKind.QUESTION,
            LogicNodeRole.PREMISE: SlideKind.EXPLANATION,
            LogicNodeRole.CONCEPT: SlideKind.CONCEPT,
            LogicNodeRole.MECHANISM: SlideKind.PROCESS,
            LogicNodeRole.METHOD: SlideKind.EXPLANATION,
            LogicNodeRole.EVIDENCE: SlideKind.EXPLANATION,
            LogicNodeRole.CASE: SlideKind.COMPARISON,
            LogicNodeRole.CONCLUSION: SlideKind.CORRECTION,
        }[role]

    def _compose_deck(
        self,
        context: PPTGenerationContext,
        logic_model: DeckLogicModel,
        storyboard: PPTStoryboard,
        visuals: dict[str, VisualModel],
    ) -> PPTDeck:
        def compose(brief: SlideBrief) -> PPTSlide:
            visual = visuals.get(brief.id)
            layout = brief.layout
            if visual is not None:
                if brief.logic_relation is None:
                    raise PPTGenerationError(
                        "composing_slides",
                        f"内容页 {brief.id} 缺少教学关系",
                    )
                layout = select_layout(
                    brief.kind,
                    VisualFamily(visual.kind),
                    brief.logic_relation,
                )
            lead, points, notes = self._compose_copy(brief, logic_model, context)
            return PPTSlide(
                id=brief.id,
                kind=brief.kind,
                title=brief.title,
                chapter_id=brief.chapter_id,
                logic_node_ids=brief.logic_node_ids,
                question=brief.question,
                claim=brief.claim,
                bridge=brief.bridge,
                logic_relation=brief.logic_relation,
                layout=layout,
                density=brief.density,
                visual=visual,
                lead=lead,
                points=points,
                speaker_notes=notes,
            )

        ordered_slides = [compose(brief) for brief in storyboard.slides]

        return PPTDeck(
            title=storyboard.title,
            language=storyboard.language,
            visual_direction=storyboard.visual_direction,
            logic_model=logic_model,
            slides=ordered_slides,
        )

    @classmethod
    def _compose_copy(
        cls,
        brief: SlideBrief,
        logic_model: DeckLogicModel,
        context: PPTGenerationContext,
    ) -> tuple[str, list[SlidePoint], str]:
        """Compile renderer-safe copy from the same semantic brief as the visual.

        Copy is not a second model-generation problem. Keeping this projection
        local makes the text, diagram, speaker notes, and page identity agree
        by construction, while the model constraints remain the final layout
        guardrail.
        """

        if brief.kind is SlideKind.COVER:
            if context.source == "path" or context.topic.lower() not in context.learning_goal.lower():
                goal_text = f"掌握{context.topic}的核心机制，理解“{logic_model.central_question}”，并能够分析与应用相关结论。"
            else:
                goal_text = context.learning_goal
            return (
                cls._text(logic_model.thesis),
                [cls._point("学习目标", goal_text)],
                f"本课围绕{context.topic}展开，先建立问题框架，再进入机制与应用。",
            )
        if brief.kind is SlideKind.ROADMAP:
            points = [
                cls._point(chapter.title, chapter.question)
                for chapter in logic_model.chapters
            ]
            return (
                "从核心问题出发，依次完成基础认知、机制理解与应用迁移。",
                points,
                "先展示完整路线，帮助学习者建立每一部分之间的前后关系。",
            )
        if brief.kind is SlideKind.SUMMARY:
            points = [
                cls._point(chapter.title, chapter.outcome)
                for chapter in logic_model.chapters
            ]
            return (
                cls._text(logic_model.thesis),
                points,
                "回到开场问题，要求学习者用自己的话串起结论与应用条件。",
            )
        nodes_by_id = {node.id: node for node in logic_model.nodes}
        source_nodes = [nodes_by_id[node_id] for node_id in brief.logic_node_ids]
        supporting_facts = list(
            dict.fromkeys(
                evidence
                for node in source_nodes
                for evidence in node.evidence
                if evidence != brief.claim
            )
        )
        return (
            cls._text(brief.claim),
            [
                cls._point(cls._point_label(index), fact)
                for index, fact in enumerate(supporting_facts[:3], start=1)
            ],
            cls._text("；".join((brief.claim, *supporting_facts[:2]))),
        )

    @classmethod
    def _point(cls, label: str, detail: str) -> SlidePoint:
        return SlidePoint(
            label=cls._text(label),
            detail=cls._text(detail),
        )

    @staticmethod
    def _patch_uncovered_nodes(
        slides: list[SlideBrief],
        logic_model: DeckLogicModel,
    ) -> list[SlideBrief]:
        """Deterministically patch storyboard so every logic node is covered.

        The LLM frequently omits one or more logic nodes from its slide
        assignments.  Rather than failing hard, we patch the storyboard:
        1. For each uncovered node, try to append it to an existing content
           slide in the same chapter (if the slide has room for more nodes,
           max 3 per slide).
        2. If no existing slide has room, insert a new content slide for the
           uncovered node at the correct chapter position.
        """
        known_nodes = {node.id for node in logic_model.nodes}
        nodes_by_id = {node.id: node for node in logic_model.nodes}
        chapters_by_id = {ch.id: ch for ch in logic_model.chapters}

        # Compute current coverage
        covered_nodes: set[str] = set()
        for slide in slides:
            if slide.kind not in {SlideKind.COVER, SlideKind.ROADMAP, SlideKind.SUMMARY}:
                covered_nodes.update(slide.logic_node_ids)

        uncovered = sorted(known_nodes - covered_nodes)
        if not uncovered:
            return slides

        logger.warning(
            "故事板 LLM 遗漏了逻辑节点 %s，正在确定性修补",
            uncovered,
        )

        # Build a mutable working copy
        result = list(slides)

        for node_id in uncovered:
            node = nodes_by_id[node_id]
            chapter_id = node.chapter_id

            # Strategy 1: append to an existing content slide in the same chapter
            # that has room (max 5 logic_node_ids per slide).
            patched = False
            for slide in result:
                if (
                    slide.kind not in {SlideKind.COVER, SlideKind.ROADMAP, SlideKind.SUMMARY}
                    and slide.chapter_id == chapter_id
                    and len(slide.logic_node_ids) < 3
                ):
                    slide.logic_node_ids.append(node_id)
                    # Auto-fill question/claim from the newly attached node if
                    # the slide currently uses the generic fallback.
                    if slide.question == "如何理解本页的核心教学点？":
                        slide.question = node.question
                    if slide.claim == slide.title:
                        slide.claim = node.claim
                    patched = True
                    logger.info(
                        "将遗漏节点 %s 追加到已有页面 %s",
                        node_id,
                        slide.id,
                    )
                    break

            if patched:
                continue

            # Strategy 2: insert a new content slide for the uncovered node.
            # Find the insertion index — right after the last slide of the
            # same chapter, or before the summary slide as a fallback.
            insert_idx = None
            for i in range(len(result) - 1, -1, -1):
                slide = result[i]
                if slide.chapter_id == chapter_id:
                    insert_idx = i + 1
                    break

            if insert_idx is None:
                # No slide for this chapter at all — insert before summary.
                for i in range(len(result) - 1, -1, -1):
                    if result[i].kind == SlideKind.SUMMARY:
                        insert_idx = i
                        break
                if insert_idx is None:
                    insert_idx = len(result)

            # Determine slide ID — renumber all slides after insertion.
            new_slide_id = f"s{insert_idx + 1:02d}"

            # Pick a kind and relation based on the node's role.
            kind = _ROLE_KIND_MAP.get(node.role, SlideKind.EXPLANATION)
            relation = _ROLE_RELATION_MAP.get(node.role, LogicRelation.SUPPORTS)
            layout = select_provisional_layout(kind, relation)

            new_slide = SlideBrief(
                id=new_slide_id,
                kind=kind,
                title=node.title[:15],
                teaching_goal=f"理解{node.title}的核心概念",
                content_focus=node.claim,
                chapter_id=chapter_id,
                logic_node_ids=[node_id],
                question=node.question,
                claim=node.claim,
                bridge=f"接下来探讨{node.title}。",
                logic_relation=relation,
                layout=layout,
                density="standard",
            )

            result.insert(insert_idx, new_slide)
            logger.info(
                "为遗漏节点 %s 插入新页面 %s（kind=%s, chapter=%s）",
                node_id,
                new_slide_id,
                kind.value,
                chapter_id,
            )

            # Renumber all slide IDs to maintain sequential order.
            for i, slide in enumerate(result):
                slide.id = f"s{i + 1:02d}"

        return result

    @staticmethod
    def _point_label(index: int) -> str:
        return ("补充事实", "应用提示", "关联线索")[min(index - 1, 2)]

    @staticmethod
    def _validate_storyboard_logic(
        storyboard: PPTStoryboard,
        logic_model: DeckLogicModel,
    ) -> None:
        if len(storyboard.slides) < 2 or storyboard.slides[1].kind.value != "roadmap":
            raise PPTGenerationError("designing_story", "第 2 页必须是全局逻辑路线页")

        known_chapters = {chapter.id for chapter in logic_model.chapters}
        known_nodes = {node.id for node in logic_model.nodes}
        covered_nodes: set[str] = set()
        completed_chapters: set[str] = set()
        active_chapter: str | None = None
        for brief in storyboard.slides:
            if brief.chapter_id is not None:
                if brief.chapter_id not in known_chapters:
                    raise PPTGenerationError(
                        "designing_story", f"页面 {brief.id} 引用了未知章节 {brief.chapter_id}"
                    )
                if brief.chapter_id != active_chapter:
                    if brief.chapter_id in completed_chapters:
                        raise PPTGenerationError("designing_story", "同一章节的页面必须连续")
                    if active_chapter is not None:
                        completed_chapters.add(active_chapter)
                    active_chapter = brief.chapter_id
            unknown_nodes = set(brief.logic_node_ids) - known_nodes
            if unknown_nodes:
                raise PPTGenerationError(
                    "designing_story", f"页面 {brief.id} 引用了未知逻辑节点 {sorted(unknown_nodes)}"
                )
            if brief.kind.value not in {"cover", "roadmap", "summary"}:
                covered_nodes.update(brief.logic_node_ids)
        missing_nodes = known_nodes - covered_nodes
        if missing_nodes:
            raise PPTGenerationError(
                "designing_story", f"故事板未覆盖逻辑节点 {sorted(missing_nodes)}"
            )

    @staticmethod
    async def _progress(callback: ProgressCallback | None, message: str, percent: int) -> None:
        if callback is not None:
            await callback(message, percent)
