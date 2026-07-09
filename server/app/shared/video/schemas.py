"""Strict contracts for the shared teaching-video pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

VideoStyleId = Literal[
    "precision_light",
    "systems_dark",
    "editorial_classroom",
]
AspectRatio = Literal["16:9", "9:16", "1:1"]
SceneRole = Literal[
    "hook",
    "concept",
    "example",
    "process",
    "misconception",
    "practice",
    "recap",
]
VisualType = Literal[
    "title_intro",
    "concept_explain",
    "process_flow",
    "state_machine",
    "data_structure",
    "algorithm_trace",
    "memory_layout",
    "cpu_architecture",
    "network_protocol",
    "layered_architecture",
    "code_execution",
    "compare_summary",
    "knowledge_check",
    "array_linked_list",
    "stack_queue",
    "process_state",
    "storage_hierarchy",
]
VisualCueKind = Literal[
    "define",
    "example",
    "trace_step",
    "compare",
    "misconception",
    "checkpoint",
    "recap",
]


# ============================================================================
# Per-visual-type 强类型数据模型
# 替代原来的 visual: dict[str, Any]，让 function_calling 看到完整 schema。
# ============================================================================

class _StepItem(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)


class _FailurePointItem(BaseModel):
    step_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class _StateItem(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)


class _TransitionItem(BaseModel):
    from_: str = Field(alias="from", min_length=1)
    to: str = Field(min_length=1)
    label: str = Field(min_length=1)

    model_config = {"populate_by_name": True}


class _EventSequenceItem(BaseModel):
    time: int
    event: str = Field(min_length=1)
    active_state: str = Field(min_length=1)


class _DataNode(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    value: str = ""


class _EdgeItem(BaseModel):
    from_: str = Field(alias="from", min_length=1)
    to: str = Field(min_length=1)
    label: str = ""

    model_config = {"populate_by_name": True}


class _OperationItem(BaseModel):
    action: str = Field(min_length=1)
    target: str = ""
    new_node: _DataNode | None = None
    description: str = Field(min_length=1)
    from_: str = Field(alias="from", default="")
    to: str = ""

    model_config = {"populate_by_name": True}


class _PointerLabelItem(BaseModel):
    name: str = Field(min_length=1)
    target: str = Field(min_length=1)


class _TraceStepItem(BaseModel):
    line: int
    description: str = Field(min_length=1)
    variables: dict[str, Any] = Field(default_factory=dict)
    highlight_indices: list[int] = Field(default_factory=list)


class _MemoryRegionItem(BaseModel):
    name: str = Field(min_length=1)
    start: str = Field(min_length=1)
    size: str = Field(min_length=1)
    color_hint: str = ""


class _MemoryActionItem(BaseModel):
    step: int
    action: str = Field(min_length=1)
    region: str = Field(min_length=1)
    detail: str = Field(min_length=1)


class _CpuModuleItem(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    description: str = Field(min_length=1)


class _DataPathItem(BaseModel):
    from_: str = Field(alias="from", min_length=1)
    to: str = Field(min_length=1)
    label: str = Field(min_length=1)
    width: str = ""

    model_config = {"populate_by_name": True}


class _CpuStepItem(BaseModel):
    phase: str = Field(min_length=1)
    description: str = Field(min_length=1)
    active_modules: list[str] = Field(default_factory=list)


class _RegisterItem(BaseModel):
    name: str = Field(min_length=1)
    value: str = Field(min_length=1)
    size: str = Field(min_length=1)


class _MessageItem(BaseModel):
    from_: str = Field(alias="from", min_length=1)
    to: str = Field(min_length=1)
    label: str = Field(min_length=1)
    detail: str = Field(min_length=1)

    model_config = {"populate_by_name": True}


class _PacketFieldItem(BaseModel):
    name: str = Field(min_length=1)
    value: str = Field(min_length=1)
    size: str = Field(min_length=1)


class _StateChangeItem(BaseModel):
    entity: str = Field(min_length=1)
    from_state: str = Field(min_length=1)
    to_state: str = Field(min_length=1)
    trigger: str = Field(min_length=1)


class _LayerItem(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    responsibility: str = Field(min_length=1)
    protocols: list[str] = Field(default_factory=list)


class _ExecStepItem(BaseModel):
    line: int
    description: str = Field(min_length=1)
    variables: dict[str, Any] = Field(default_factory=dict)
    output: str = ""


class _CompareSide(BaseModel):
    title: str = Field(min_length=1)
    points: list[str] = Field(min_length=1)


class _DiffDimensionItem(BaseModel):
    dimension: str = Field(min_length=1)
    left: str = Field(min_length=1)
    right: str = Field(min_length=1)


class _OptionItem(BaseModel):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class _ArrayNodeItem(BaseModel):
    id: str = Field(min_length=1)
    value: str = Field(min_length=1)
    index: int


class _ArrayOperationItem(BaseModel):
    type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    target_index: int | None = None
    value: str = ""


class _StackQueueItem(BaseModel):
    value: str = Field(min_length=1)
    status: str = Field(min_length=1)


class _StackQueueOperationItem(BaseModel):
    type: str = Field(min_length=1)
    value: str = ""
    description: str = Field(min_length=1)


class _ProcessStateItem(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    color_hint: str = ""


class _ProcessTransitionItem(BaseModel):
    from_: str = Field(alias="from", min_length=1)
    to: str = Field(min_length=1)
    trigger: str = Field(min_length=1)
    description: str = Field(min_length=1)

    model_config = {"populate_by_name": True}


class _StorageLevelItem(BaseModel):
    name: str = Field(min_length=1)
    speed: str = Field(min_length=1)
    capacity: str = Field(min_length=1)
    cost: str = Field(min_length=1)
    examples: list[str] = Field(default_factory=list)


class _StorageTransferItem(BaseModel):
    from_: str = Field(alias="from", min_length=1)
    to: str = Field(min_length=1)
    method: str = Field(min_length=1)
    speed: str = Field(min_length=1)

    model_config = {"populate_by_name": True}


class _RelatedConceptItem(BaseModel):
    name: str = Field(min_length=1)
    relation: str = Field(min_length=1)


# ── 17 个 visual data model ──

class TitleIntroVisual(BaseModel):
    course: str = Field(min_length=1)
    chapter: str = Field(min_length=1)
    subtitle: str = ""
    tags: list[str] = Field(default_factory=list)
    hero_keywords: list[str] = Field(default_factory=list)
    hero_center: str = ""


class ConceptExplainVisual(BaseModel):
    main_concept: str = Field(min_length=1)
    definition: str = Field(min_length=1)
    keywords: list[str] = Field(default_factory=list)
    why_it_matters: list[str] = Field(default_factory=list)
    related_concepts: list[_RelatedConceptItem] = Field(default_factory=list)
    common_misconception: str = ""


class ProcessFlowVisual(BaseModel):
    process_name: str = Field(min_length=1)
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    steps: list[_StepItem] = Field(min_length=1)
    failure_points: list[_FailurePointItem] = Field(default_factory=list)


class StateMachineVisual(BaseModel):
    machine_name: str = Field(min_length=1)
    initial_state: str = Field(min_length=1)
    states: list[_StateItem] = Field(min_length=1)
    transitions: list[_TransitionItem] = Field(min_length=1)
    event_sequence: list[_EventSequenceItem] = Field(default_factory=list)
    explanation_map: dict[str, str] = Field(default_factory=dict)


class DataStructureVisual(BaseModel):
    structure_type: str = Field(min_length=1)
    initial_state: dict[str, Any] = Field(min_length=1)
    operations: list[_OperationItem] = Field(default_factory=list)
    pointer_labels: list[_PointerLabelItem] = Field(default_factory=list)
    complexity: dict[str, str] = Field(default_factory=dict)
    invariant: str = ""


class AlgorithmTraceVisual(BaseModel):
    algorithm_name: str = Field(min_length=1)
    problem: str = Field(min_length=1)
    data: list[int | str] = Field(default_factory=list)
    pseudocode: list[str] = Field(default_factory=list)
    steps: list[_TraceStepItem] = Field(min_length=1)
    complexity: dict[str, str] = Field(default_factory=dict)
    result: str = ""


class MemoryLayoutVisual(BaseModel):
    layout_type: str = Field(min_length=1)
    code: str = Field(min_length=1)
    memory_regions: list[_MemoryRegionItem] = Field(min_length=1)
    actions: list[_MemoryActionItem] = Field(default_factory=list)
    explanation: str = Field(min_length=1)


class CpuArchitectureVisual(BaseModel):
    architecture_name: str = Field(min_length=1)
    current_instruction: str = Field(min_length=1)
    modules: list[_CpuModuleItem] = Field(min_length=1)
    data_paths: list[_DataPathItem] = Field(default_factory=list)
    steps: list[_CpuStepItem] = Field(default_factory=list)
    registers: list[_RegisterItem] = Field(default_factory=list)
    explanation: str = Field(min_length=1)


class NetworkProtocolVisual(BaseModel):
    protocol_name: str = Field(min_length=1)
    messages: list[_MessageItem] = Field(min_length=1)
    packet_fields: list[_PacketFieldItem] = Field(default_factory=list)
    state_changes: list[_StateChangeItem] = Field(default_factory=list)
    key_point: str = Field(min_length=1)


class LayeredArchitectureVisual(BaseModel):
    architecture_name: str = Field(min_length=1)
    layers: list[_LayerItem] = Field(min_length=1)
    current_focus_layer: str = Field(min_length=1)
    examples: list[str] = Field(default_factory=list)


class CodeExecutionVisual(BaseModel):
    language: str = Field(min_length=1)
    code: str = Field(min_length=1)
    steps: list[_ExecStepItem] = Field(min_length=1)
    output: str = ""
    error_or_misconception: str = ""


class CompareSummaryVisual(BaseModel):
    compare_title: str = Field(min_length=1)
    left: _CompareSide
    right: _CompareSide
    same_points: list[str] = Field(default_factory=list)
    different_points: list[_DiffDimensionItem] = Field(default_factory=list)
    conclusion: str = Field(min_length=1)
    exam_hint: str = ""


class KnowledgeCheckVisual(BaseModel):
    question: str = Field(min_length=1)
    options: list[_OptionItem] = Field(min_length=1)
    correct_answer: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    related_concept: str = ""
    review_points: list[str] = Field(default_factory=list)


class ArrayLinkedListVisual(BaseModel):
    structure_type: str = Field(min_length=1)
    nodes: list[_ArrayNodeItem] = Field(min_length=1)
    operations: list[_ArrayOperationItem] = Field(default_factory=list)
    time_complexity: str = ""
    space_complexity: str = ""


class StackQueueVisual(BaseModel):
    structure_type: str = Field(min_length=1)
    items: list[_StackQueueItem] = Field(min_length=1)
    operations: list[_StackQueueOperationItem] = Field(default_factory=list)


class ProcessStateVisual(BaseModel):
    states: list[_ProcessStateItem] = Field(min_length=1)
    transitions: list[_ProcessTransitionItem] = Field(min_length=1)


class StorageHierarchyVisual(BaseModel):
    levels: list[_StorageLevelItem] = Field(min_length=1)
    transfers: list[_StorageTransferItem] = Field(default_factory=list)
    highlight_level: str = ""


# ── visual_type → model 映射 ──

_VISUAL_TYPE_MODELS: dict[str, type[BaseModel]] = {
    "title_intro": TitleIntroVisual,
    "concept_explain": ConceptExplainVisual,
    "process_flow": ProcessFlowVisual,
    "state_machine": StateMachineVisual,
    "data_structure": DataStructureVisual,
    "algorithm_trace": AlgorithmTraceVisual,
    "memory_layout": MemoryLayoutVisual,
    "cpu_architecture": CpuArchitectureVisual,
    "network_protocol": NetworkProtocolVisual,
    "layered_architecture": LayeredArchitectureVisual,
    "code_execution": CodeExecutionVisual,
    "compare_summary": CompareSummaryVisual,
    "knowledge_check": KnowledgeCheckVisual,
    "array_linked_list": ArrayLinkedListVisual,
    "stack_queue": StackQueueVisual,
    "process_state": ProcessStateVisual,
    "storage_hierarchy": StorageHierarchyVisual,
}


def scene_draft_for(visual_type: VisualType) -> type[BaseModel]:
    """根据 visual_type 返回对应的 SceneDraft 子类。

    每个 visual_type 有自己的强类型 visual 字段，替代原来的 dict[str, Any]。
    这让 function_calling 看到完整的 JSON schema，大幅提升结构化输出可靠性。
    """
    from pydantic import create_model

    visual_model = _VISUAL_TYPE_MODELS.get(visual_type)
    if visual_model is None:
        return SceneDraft

    # 用 create_model 动态创建带强类型 visual 的 SceneDraft 子类
    # 继承 SceneDraft 的所有字段，但将 visual 从 dict[str, Any] 替换为具体类型
    return create_model(
        f"SceneDraft_{visual_type}",
        __base__=SceneDraft,
        visual=(visual_model, ...),
    )


class SourceMaterial(BaseModel):
    source_id: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    title: str = ""
    content: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VideoRequest(BaseModel):
    topic: str = Field(min_length=1)
    audience: str = ""
    learning_goal: str = ""
    duration_seconds: int = Field(default=180, ge=60, le=600)
    scene_count: int = Field(default=6, ge=3, le=12)
    aspect_ratio: AspectRatio = "16:9"
    language: str = "zh-CN"
    voice: str = "teacher"
    include_captions: bool = True
    style_hint: VideoStyleId | None = None
    narrative_focus: Literal["concept", "process", "comparison", "practice"] | None = None
    materials: list[SourceMaterial] = Field(min_length=1)
    output_dir: Path
    metadata: dict[str, Any] = Field(default_factory=dict)


class VideoStyleDecision(BaseModel):
    id: VideoStyleId
    rationale: str = Field(min_length=1)


class VideoMaterialDigest(BaseModel):
    topic: str = Field(min_length=1)
    audience: str = ""
    learning_goal: str = ""
    core_concepts: list[str] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    process_steps: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    practice_prompts: list[str] = Field(default_factory=list)
    visual_opportunities: list[str] = Field(default_factory=list)
    source_map: dict[str, list[str]] = Field(default_factory=dict)


class SceneContract(BaseModel):
    scene_id: str = Field(min_length=1)
    index: int = Field(ge=1)
    role: SceneRole
    title: str = Field(min_length=1)
    learning_objective: str = Field(min_length=1)
    visual_type: VisualType
    content_hint: str = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)


class VideoOutline(BaseModel):
    title: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    narrative: str = Field(min_length=1)
    style: VideoStyleDecision
    scenes: list[SceneContract] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scenes(self) -> "VideoOutline":
        indexes = [scene.index for scene in self.scenes]
        if indexes != list(range(1, len(self.scenes) + 1)):
            raise ValueError("outline scene indexes must be contiguous")
        if self.scenes[0].role != "hook":
            raise ValueError("outline must begin with a hook")
        if self.scenes[-1].role != "recap":
            raise ValueError("outline must end with a recap")
        return self


class VisualBeatDraft(BaseModel):
    id: str = Field(min_length=1)
    kind: VisualCueKind
    target: str = ""
    text_anchor: str = Field(min_length=1)
    summary: str = ""


class SceneDraft(BaseModel):
    scene_id: str = Field(min_length=1)
    index: int = Field(ge=1)
    title: str = Field(min_length=1)
    narration: str = Field(min_length=1)
    visual_type: VisualType
    visual: dict[str, Any] = Field(min_length=1)
    visual_beats: list[VisualBeatDraft] = Field(default_factory=list)


class RenderSettings(BaseModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: int = Field(default=30, ge=24, le=60)
    video_codec: Literal["h264"] = "h264"
    audio_codec: Literal["aac"] = "aac"
    format: Literal["mp4"] = "mp4"


class CaptionWord(BaseModel):
    text: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_timing(self) -> "CaptionWord":
        if self.end_ms <= self.start_ms:
            raise ValueError("caption word end_ms must be greater than start_ms")
        return self


class AudioSynthesis(BaseModel):
    path: Path
    duration_ms: int = Field(gt=0)
    words: list[CaptionWord] = Field(default_factory=list)


class CaptionChunk(BaseModel):
    text: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_timing(self) -> "CaptionChunk":
        if self.end_ms <= self.start_ms:
            raise ValueError("caption chunk end_ms must be greater than start_ms")
        return self


class VisualCue(BaseModel):
    id: str = Field(min_length=1)
    kind: VisualCueKind
    target: str = ""
    summary: str = ""
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    caption_text: str | None = None

    @model_validator(mode="after")
    def validate_timing(self) -> "VisualCue":
        if self.end_ms <= self.start_ms:
            raise ValueError("visual cue end_ms must be greater than start_ms")
        return self


class VideoScene(BaseModel):
    scene_id: str = Field(min_length=1)
    index: int = Field(ge=1)
    role: SceneRole
    title: str = Field(min_length=1)
    learning_objective: str = Field(min_length=1)
    visual_type: VisualType
    visual: dict[str, Any] = Field(min_length=1)
    narration: str = Field(min_length=1)
    audio_src: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    duration_ms: int = Field(gt=0)
    audio_duration_ms: int = Field(gt=0)
    caption_words: list[CaptionWord] = Field(default_factory=list)
    captions: list[CaptionChunk] = Field(default_factory=list)
    visual_cues: list[VisualCue] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_timeline(self) -> "VideoScene":
        if self.audio_duration_ms > self.duration_ms:
            raise ValueError("audio duration exceeds scene duration")
        if any(word.end_ms > self.audio_duration_ms for word in self.caption_words):
            raise ValueError("caption word timing exceeds measured audio")
        if any(chunk.end_ms > self.audio_duration_ms for chunk in self.captions):
            raise ValueError("caption timing exceeds measured audio")
        if any(cue.end_ms > self.audio_duration_ms for cue in self.visual_cues):
            raise ValueError("visual cue timing exceeds measured audio")
        return self


class VideoPlan(BaseModel):
    schema_version: Literal["video/v2"] = "video/v2"
    title: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    language: str = "zh-CN"
    aspect_ratio: AspectRatio
    style: VideoStyleDecision
    render: RenderSettings
    scenes: list[VideoScene] = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_scene_sequence(self) -> "VideoPlan":
        expected_start = 0
        for expected_index, scene in enumerate(self.scenes, start=1):
            if scene.index != expected_index:
                raise ValueError("scene indexes must be contiguous")
            if scene.start_ms != expected_start:
                raise ValueError("scene starts must be contiguous")
            expected_start += scene.duration_ms
        return self

    @property
    def duration_ms(self) -> int:
        return sum(scene.duration_ms for scene in self.scenes)


class VideoArtifact(BaseModel):
    plan: VideoPlan
    mp4_path: Path
    public_url: str = Field(min_length=1)
    duration_ms: int = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    size_bytes: int = Field(gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
