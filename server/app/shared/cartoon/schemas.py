"""Structured contracts for deterministic animated teaching videos.

面向计算机理论知识的动画演示 — 通用可视化原语体系。
支持数据结构、算法、数学、数据库、编译原理、操作系统、离散数学等
所有计算机本科理论课程的动态演示。

核心设计：不按学科分类，按可视化模式分类。
LLM 根据 learning_need 自动选择合适的可视化模式组合。
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


# ===================== Visual Kind — 通用可视化原语 =====================
#
# 设计原则：
# - 每个 kind 描述"这个元素在视觉上是什么形态"，而非"它属于哪个学科"
# - 同一个 kind 可跨学科复用（node 既是树节点也是 ER 实体也是 NFA 状态）
# - 学科差异由 prompt 根据 learning_need 自动推断，不写死在 schema 里

VisualKind = Literal[
    # ── 通用元素 ──
    "node",         # 通用节点 — 任何离散对象（概念、实体、状态、处理器）
    "label",        # 纯文本标签 — 注释、说明、标题
    "code",         # 代码块 — 代码行、伪代码
    "metric",       # 数值指标 — 计数器、复杂度、命中率
    "formula",      # 公式展示 — 数学公式、等式、不等式
    "packet",       # 数据包/消息 — 网络包、请求/响应、信号

    # ── 结构类元素（树/图/ER/语法树等） ──
    "cell",         # 格子/槽位 — 数组格子、哈希桶、寄存器、页表项
    "state",        # 状态指示器 — 自动机状态、进程状态、协议状态
    "step",         # 步骤/阶段 — 流程步骤、推导步骤、证明步骤

    # ── 容器类元素 ──
    "array",        # 数组容器 — items 为格子内容
    "stack",        # 栈容器 — items 自底向上排列
    "queue",        # 队列容器 — items 从左到右排列
    "table",        # 表格容器 — items 为行内容（数据库表、真值表、关系表）
]


# ===================== Animation Action — 通用操作型动画 =====================

AnimationAction = Literal[
    # ── 基础动画 ──
    "reveal",       # 首次出现（淡入）
    "focus",        # 聚焦强调
    "transfer",     # 数据/请求沿连接传递
    "compare",      # 同时强调对比对象
    "swap",         # 两个元素位置互换
    "traverse",     # 按 targets 顺序逐个高亮
    "branch",       # 展开分支
    "state_change", # 状态变化（改背景色/显示内容）
    "count",        # 数值增长

    # ── 操作型动画（优先使用） ──
    "insert",       # 元素从指定方向滑入到位置
    "remove",       # 元素从位置滑出消失
    "highlight_path",  # 高亮路径上的节点 and 边
    "value_change",    # 元素的值发生变化
    "shift",           # 一组元素整体平移
    "highlight_code",  # 高亮代码行

    # ── 推导型动画 ──
    "derive",       # 公式/等式的推导变换（源元素淡出，结果淡入）
    "transform",    # 结构变换（如 NFA→DFA、语法树归约）
]


# ===================== Scene Layout & Role =====================

SceneRole = Literal[
    "hook",
    "concept",
    "process",
    "compare",
    "architecture",
    "code_trace",
    "derivation",   # 推导/证明场景
    "recap",
]

SceneLayout = Literal[
    "hero",         # 单一核心元素
    "flow",         # 流程图，元素按顺序排列
    "compare",      # 对比视图，左右分栏
    "stack",        # 栈视图，元素纵向堆叠
    "tree",         # 树/层次结构，节点绝对定位 + edges
    "graph",        # 图/网络结构，节点绝对定位 + edges
    "state_diagram", # 状态机/自动机，状态节点 + transitions
    "code",         # 代码执行轨迹
    "array_view",   # 数组/表格行视图，格子横向排列
    "queue_view",   # 队列视图，左入口右出口
    "table_view",   # 表格视图，行列结构（数据库表、真值表）
    "derivation",   # 推导链视图，公式/等式逐步变换
    "grid",         # 多元素网格
    "recap",        # 总结回顾
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
    label: str = Field(default="", max_length=80)
    detail: str = Field(default="", max_length=160)
    items: list[str] = Field(default_factory=list, max_length=8)
    value: str = Field(default="", max_length=40)
    # 绝对定位坐标（用于 tree/graph/state_diagram 等需要精确定位的布局）
    x: int | None = None
    y: int | None = None


# ===================== Visual Connection — 边和指针 =====================

class VisualConnection(StrictModel):
    source: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    target: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    label: str = Field(default="", max_length=30)
    kind: Literal["edge", "pointer", "arrow", "transition"] = "edge"
    # transition 的触发条件（如状态机转换条件）
    condition: str = Field(default="", max_length=30)


# ===================== Animation Cue =====================

class AnimationCue(StrictModel):
    """A semantic action anchored to a spoken keyword."""

    action: AnimationAction
    targets: list[str] = Field(min_length=1, max_length=6)
    keyword: str = Field(default="", max_length=24)
    # insert/remove 的方向
    direction: Literal["left", "right", "top", "bottom"] = "top"
    # highlight_path 的节点序列
    path: list[str] = Field(default_factory=list, max_length=8)
    # value_change 的新值
    new_value: str = Field(default="", max_length=40)
    # derive/transform 的结果元素 ID
    result: str = Field(default="", max_length=32)


# ===================== Scene Brief =====================

class SceneBrief(StrictModel):
    role: SceneRole
    title: str = Field(min_length=1, max_length=48)
    narration: str = Field(min_length=1, max_length=360)
    layout: SceneLayout
    elements: list[VisualElement] = Field(min_length=1, max_length=24)
    connections: list[VisualConnection] = Field(default_factory=list, max_length=24)
    cues: list[AnimationCue] = Field(default_factory=list, max_length=24)
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


# ===================== Cartoon Video Request — 4 参数影响 HTML 输出 =====================

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
