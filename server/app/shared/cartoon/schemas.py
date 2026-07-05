"""Structured contracts for deterministic animated teaching videos.

面向计算机理论知识的动画演示 — 支持树、图、队列、栈、链表等数据结构的动态操作演示。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceArtifact(StrictModel):
    agent_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    materials: list[str] = Field(default_factory=list, max_length=12)


# ===================== Visual Kind — 数据结构可视化原语 =====================

VisualKind = Literal[
    # 通用节点
    "node",
    "label",
    "code",
    "metric",
    "formula",
    "packet",
    # 状态
    "state",
    # 数据结构（新增）
    "tree_node",    # 树节点 — 圆形/圆角方块，显示值，可连边
    "graph_node",   # 图节点 — 圆形，显示标签，可连边
    "cell",         # 数组格子 — 带索引的方块，显示值
    "pointer",      # 指针/引用 — 箭头指向目标
    # 容器
    "array",
    "stack",
    "queue",
]


# ===================== Animation Action — 操作型动画 =====================

AnimationAction = Literal[
    # 基础动画
    "reveal",       # 首次出现（淡入）
    "focus",        # 聚焦强调
    "transfer",     # 数据/请求沿连接传递
    "compare",      # 同时强调对比对象
    "swap",         # 两个元素位置互换
    "traverse",     # 按 targets 顺序逐个高亮
    "branch",       # 展开分支
    "state_change", # 状态变化（改背景色）
    "count",        # 数值增长
    # 操作型动画（新增）
    "insert",       # 元素从指定方向滑入到位置
    "remove",       # 元素从位置滑出消失
    "highlight_path",  # 高亮路径上的节点和边
    "value_change",    # 元素的值发生变化
    "shift",           # 一组元素整体平移
]


# ===================== Scene Layout & Role =====================

SceneRole = Literal[
    "hook",
    "concept",
    "process",
    "compare",
    "architecture",
    "code_trace",
    "recap",
]

SceneLayout = Literal[
    "hero",
    "flow",
    "compare",
    "stack",
    "tree",
    "graph",        # 新增：图布局
    "code",
    "array_view",   # 新增：数组视图
    "queue_view",   # 新增：队列视图
    "grid",
    "recap",
]


class CaptionWord(StrictModel):
    text: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)


# ===================== Visual Element =====================

class VisualElement(StrictModel):
    """A semantic teaching object rendered by the deterministic compiler."""

    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    kind: VisualKind
    label: str = Field(min_length=1, max_length=80)
    detail: str = Field(default="", max_length=160)
    items: list[str] = Field(default_factory=list, max_length=8)
    value: str = Field(default="", max_length=40)
    # 新增：位置坐标（用于 tree/graph 绝对定位）
    x: int | None = None
    y: int | None = None


# ===================== Visual Connection — 边和指针 =====================

class VisualConnection(StrictModel):
    source: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    target: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    label: str = Field(default="", max_length=30)
    kind: Literal["edge", "pointer", "arrow"] = "edge"  # 新增：连接类型


# ===================== Animation Cue =====================

class AnimationCue(StrictModel):
    """A semantic action anchored to a spoken keyword."""

    action: AnimationAction
    targets: list[str] = Field(min_length=1, max_length=6)
    keyword: str = Field(default="", max_length=24)
    # 新增：操作型动画参数
    direction: Literal["left", "right", "top", "bottom"] = "top"  # insert/remove 的方向
    path: list[str] = Field(default_factory=list, max_length=8)   # highlight_path 的节点序列
    new_value: str = Field(default="", max_length=40)             # value_change 的新值


# ===================== Scene Brief =====================

class SceneBrief(StrictModel):
    role: SceneRole
    title: str = Field(min_length=1, max_length=48)
    narration: str = Field(min_length=1, max_length=360)
    layout: SceneLayout
    elements: list[VisualElement] = Field(min_length=1, max_length=10)
    connections: list[VisualConnection] = Field(default_factory=list, max_length=12)
    cues: list[AnimationCue] = Field(default_factory=list, max_length=12)
    callout: str = Field(default="", max_length=80)

    # Runtime-only fields populated from Edge TTS.
    start_time: float = Field(default=0.0, ge=0.0)
    duration: float = Field(default=1.0, gt=0.0)
    audio_path: str | None = None
    words: list[CaptionWord] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_references(self) -> "SceneBrief":
        element_ids = {element.id for element in self.elements}
        self.connections = [
            connection
            for connection in self.connections
            if connection.source in element_ids and connection.target in element_ids
        ]
        for cue in self.cues:
            cue.targets = [target for target in cue.targets if target in element_ids]
            if cue.path:
                cue.path = [node for node in cue.path if node in element_ids]
        self.cues = [cue for cue in self.cues if cue.targets]
        return self


# ===================== Video Brief =====================

class VideoBrief(StrictModel):
    title: str = Field(min_length=1, max_length=60)
    subject: str = Field(min_length=1, max_length=40)
    summary: str = Field(min_length=1, max_length=140)
    scenes: list[SceneBrief] = Field(min_length=3, max_length=16)
    total_duration: float = Field(default=0.0, ge=0.0)

    @model_validator(mode="after")
    def validate_story_arc(self) -> "VideoBrief":
        if self.scenes[0].role != "hook":
            raise ValueError("第一个场景必须是 hook")
        if self.scenes[-1].role != "recap":
            raise ValueError("最后一个场景必须是 recap")
        return self


# ===================== Static Audit =====================

class StaticAudit(StrictModel):
    passed: bool
    problems: list[str] = Field(default_factory=list)
    scene_count: int = Field(ge=0)


# ===================== Cartoon Video Request — 重构参数 =====================

class CartoonVideoRequest(StrictModel):
    """动画视频生成请求 — 4 个参数全部影响 HTML 输出。"""

    learning_need: str = Field(min_length=1)
    profile: dict[str, Any] | str

    # 视觉风格 — 影响 CSS 主题配色
    style: Literal["diagram", "minimal", "dark_tech", "chalkboard"] = "diagram"

    # 讲解深度 — 影响 Prompt 约束（旁白字数、场景数、cue 类型）
    depth: Literal["overview", "standard", "deep"] = "standard"

    # 动画节奏 — 影响 Compiler GSAP duration/stagger
    pace: Literal["fast", "normal", "slow"] = "normal"

    # 画面丰富度 — 影响 element 数量、connections、标注渲染
    visuals: Literal["clean", "balanced", "detailed"] = "balanced"

    output_dir: Path
    artifacts: list[SourceArtifact] = Field(default_factory=list)
