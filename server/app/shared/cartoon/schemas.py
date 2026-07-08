"""Structured contracts for deterministic animated teaching videos.

面向计算机理论知识的动画演示 — 通用可视化原语体系。
支持数据结构、算法、数学、数据库、编译原理、操作系统、离散数学等
所有计算机本科理论课程的动态演示。

核心设计：不按学科分类，按可视化模式分类。
LLM 根据 learning_need 自动选择合适的可视化模式组合。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _coerce_enum(
    value: Any,
    valid: tuple[str, ...],
    default: str,
    mapping: dict[str, str] | None = None,
) -> str:
    """枚举容错归一化：映射已知别名，未知值回落到默认值，绝不抛 Literal 校验错误。

    生成可靠性优先于枚举完美——LLM 偶发产出 schema 外的枚举值时，强制归一化到
    语义最通用的默认值，保证只要结构正确就能通过校验，避免整个分镜生成失败。
    """
    if value is None:
        return default
    s = str(value).strip().lower()
    if mapping and s in mapping:
        return mapping[s]
    if s in valid:
        return s
    return default


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

# 各 Literal 枚举的合法值集合，供 _coerce_enum 使用（必须在 Literal 定义之后）。
_VISUAL_KINDS = get_args(VisualKind)
_ANIMATION_ACTIONS = get_args(AnimationAction)
_SCENE_ROLES = get_args(SceneRole)
_SCENE_LAYOUTS = get_args(SceneLayout)


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
    detail: str = Field(default="", max_length=1000)
    items: list[str] = Field(default_factory=list, max_length=30)
    value: str = Field(default="", max_length=1000)
    # 坐标由编译器自动计算，LLM 不再提供 x/y

    @field_validator("id", mode="before")
    @classmethod
    def normalize_id(cls, value: Any) -> str:
        if value is None:
            return ""
        s = str(value).strip().lower()
        if s and not s[0].isalpha():
            s = "n" + s
        import re
        s = re.sub(r"[^a-z0-9_-]", "_", s)
        return s[:32]

    @field_validator("kind", mode="before")
    @classmethod
    def normalize_kind(cls, value: str) -> str:
        mapping = {
            "text": "label",
            "header": "label",
            "list_item": "step",
            "array_view": "array",
            "array_cell": "cell",
            "list": "array",
            "box": "node",
            "rect": "node",
            "circle": "node",
            "block": "node",
            "pointer": "node",
            "card": "node",
        }
        return _coerce_enum(value, _VISUAL_KINDS, "node", mapping)

    @field_validator("items", mode="before")
    @classmethod
    def normalize_items(cls, value: Any) -> Any:
        if isinstance(value, list):
            return [str(x) for x in value]
        if isinstance(value, str):
            if value.startswith("[") and value.endswith("]"):
                try:
                    import ast
                    parsed = ast.literal_eval(value)
                    if isinstance(parsed, list):
                        return [str(x) for x in parsed]
                except Exception:
                    pass
            if "," in value:
                return [x.strip() for x in value.split(",")]
        return value


# ===================== Visual Connection — 边和指针 =====================

class VisualConnection(StrictModel):
    source: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    target: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    label: str = Field(default="", max_length=30)
    kind: Literal["edge", "pointer", "arrow", "transition"] = "edge"
    # transition 的触发 condition
    condition: str = Field(default="", max_length=30)

    @field_validator("kind", mode="before")
    @classmethod
    def normalize_conn_kind(cls, value: Any) -> str:
        return _coerce_enum(value, ("edge", "pointer", "arrow", "transition"), "edge")

    @field_validator("source", "target", mode="before")
    @classmethod
    def normalize_conn_id(cls, value: Any) -> str:
        if value is None:
            return ""
        s = str(value).strip().lower()
        if s and not s[0].isalpha():
            s = "n" + s
        import re
        s = re.sub(r"[^a-z0-9_-]", "_", s)
        return s[:32]


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

    @field_validator("action", mode="before")
    @classmethod
    def normalize_action(cls, value: str) -> str:
        mapping = {
            "highlight": "focus",
            "select": "focus",
            "fade_in": "reveal",
            "animate": "reveal",
            "move": "reveal",
            "connect": "reveal",
            "highlight_line": "highlight_code",
            "highlight_lines": "highlight_code",
        }
        return _coerce_enum(value, _ANIMATION_ACTIONS, "reveal", mapping)

    @field_validator("direction", mode="before")
    @classmethod
    def normalize_direction(cls, value: Any) -> Any:
        return _coerce_enum(value, ("left", "right", "top", "bottom"), "top")

    @field_validator("targets", "path", mode="before")
    @classmethod
    def normalize_cue_ids(cls, value: Any) -> Any:
        if isinstance(value, list):
            res = []
            for item in value:
                s = str(item).strip().lower()
                if s and not s[0].isalpha():
                    s = "n" + s
                import re
                s = re.sub(r"[^a-z0-9_-]", "_", s)
                res.append(s[:32])
            return res
        return value


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

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, value: Any) -> Any:
        return _coerce_enum(value, _SCENE_ROLES, "concept")

    @field_validator("layout", mode="before")
    @classmethod
    def normalize_layout(cls, value: Any) -> Any:
        return _coerce_enum(value, _SCENE_LAYOUTS, "flow")

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
    teaching_plan: str | None = None

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


# ============================================================================
# SIMPLIFIED SCHEMA — LLM 只需输出这些，枚举组合从 22,984 降到 108
# ============================================================================
#
# 设计原则：
# - LLM 只需从 3 种 kind / 3 种 action / 3 种 layout / 4 种 role 中选择
# - 桥接层 (bridge_simple_to_brief) 将简化枚举确定性映射到完整 VideoBrief
# - compiler / pipeline / renderer 完全不改，下游看到的仍是完整 VideoBrief
#
# 简化映射：
#   SimpleKind  → VisualKind:  node→node, label→label, metric→metric
#   SimpleAction → AnimationAction: reveal→reveal, focus→focus, insert→insert
#   SimpleLayout → SceneLayout: tree→tree, flow→flow, recap→recap
#   SimpleRole  → SceneRole: hook→hook, process→process, compare→compare, recap→recap
#
# 编译器根据 layout 自动推断更精确的 kind/action：
#   tree layout + node → 圆形节点 + edge connections
#   flow layout + node → 流程节点 + arrow connections
#   recap layout + label → 总结卡片
# ============================================================================

SimpleKind = Literal["node", "label", "metric"]
SimpleAction = Literal["reveal", "focus", "insert"]
SimpleLayout = Literal["tree", "flow", "recap"]
SimpleRole = Literal["hook", "process", "compare", "recap"]

_SIMPLE_KINDS = get_args(SimpleKind)
_SIMPLE_ACTIONS = get_args(SimpleAction)
_SIMPLE_LAYOUTS = get_args(SimpleLayout)
_SIMPLE_ROLES = get_args(SimpleRole)


class SimpleElement(StrictModel):
    """简化可视化元素 — LLM 只需选 node/label/metric 三种。"""

    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    kind: SimpleKind
    label: str = Field(default="", max_length=80)
    value: str = Field(default="", max_length=200)
    items: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("id", mode="before")
    @classmethod
    def normalize_id(cls, value: Any) -> str:
        if value is None:
            return ""
        s = str(value).strip().lower()
        if s and not s[0].isalpha():
            s = "n" + s
        import re
        s = re.sub(r"[^a-z0-9_-]", "_", s)
        return s[:32]

    @field_validator("kind", mode="before")
    @classmethod
    def normalize_kind(cls, value: Any) -> str:
        mapping = {
            "text": "label", "header": "label", "step": "label",
            "cell": "node", "state": "node", "box": "node",
            "array": "node", "stack": "node", "queue": "node",
            "table": "node", "code": "label", "formula": "label",
            "packet": "node", "pointer": "node",
        }
        return _coerce_enum(value, _SIMPLE_KINDS, "node", mapping)

    @field_validator("items", mode="before")
    @classmethod
    def normalize_items(cls, value: Any) -> Any:
        if isinstance(value, list):
            return [str(x) for x in value]
        if isinstance(value, str):
            if value.startswith("[") and value.endswith("]"):
                try:
                    import ast
                    parsed = ast.literal_eval(value)
                    if isinstance(parsed, list):
                        return [str(x) for x in parsed]
                except Exception:
                    pass
            if "," in value:
                return [x.strip() for x in value.split(",")]
        return value


class SimpleConnection(StrictModel):
    """简化连接 — 只需 source/target/label，kind 由桥接层推断。"""

    source: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    target: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$")
    label: str = Field(default="", max_length=30)

    @field_validator("source", "target", mode="before")
    @classmethod
    def normalize_conn_id(cls, value: Any) -> str:
        if value is None:
            return ""
        s = str(value).strip().lower()
        if s and not s[0].isalpha():
            s = "n" + s
        import re
        s = re.sub(r"[^a-z0-9_-]", "_", s)
        return s[:32]


class SimpleCue(StrictModel):
    """简化动画指令 — LLM 只需选 reveal/focus/insert 三种。"""

    action: SimpleAction
    targets: list[str] = Field(min_length=1, max_length=6)
    keyword: str = Field(default="", max_length=24)
    direction: Literal["left", "right", "top", "bottom"] = "top"

    @field_validator("action", mode="before")
    @classmethod
    def normalize_action(cls, value: Any) -> str:
        mapping = {
            "highlight": "focus", "select": "focus", "emphasize": "focus",
            "fade_in": "reveal", "animate": "reveal", "move": "reveal",
            "show": "reveal", "appear": "reveal",
            "add": "insert", "push": "insert", "slide_in": "insert",
            "swap": "insert", "remove": "insert", "shift": "insert",
            "transfer": "insert", "traverse": "focus",
            "highlight_path": "focus", "value_change": "insert",
            "state_change": "insert", "branch": "insert",
            "derive": "insert", "transform": "insert",
            "count": "insert", "highlight_code": "focus",
        }
        return _coerce_enum(value, _SIMPLE_ACTIONS, "reveal", mapping)

    @field_validator("direction", mode="before")
    @classmethod
    def normalize_direction(cls, value: Any) -> Any:
        return _coerce_enum(value, ("left", "right", "top", "bottom"), "top")

    @field_validator("targets", mode="before")
    @classmethod
    def normalize_cue_ids(cls, value: Any) -> Any:
        if isinstance(value, list):
            res = []
            for item in value:
                s = str(item).strip().lower()
                if s and not s[0].isalpha():
                    s = "n" + s
                import re
                s = re.sub(r"[^a-z0-9_-]", "_", s)
                res.append(s[:32])
            return res
        return value


class SimpleScene(StrictModel):
    """简化场景 — LLM 只需选 tree/flow/recap 三种布局。"""

    role: SimpleRole
    title: str = Field(min_length=1, max_length=48)
    narration: str = Field(min_length=1, max_length=360)
    layout: SimpleLayout
    elements: list[SimpleElement] = Field(min_length=1, max_length=24)
    connections: list[SimpleConnection] = Field(default_factory=list, max_length=24)
    cues: list[SimpleCue] = Field(default_factory=list, max_length=24)
    callout: str = Field(default="", max_length=80)

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, value: Any) -> Any:
        mapping = {
            "concept": "process", "architecture": "process",
            "code_trace": "process", "derivation": "process",
        }
        return _coerce_enum(value, _SIMPLE_ROLES, "process", mapping)

    @field_validator("layout", mode="before")
    @classmethod
    def normalize_layout(cls, value: Any) -> str:
        mapping = {
            "hero": "flow", "graph": "tree", "state_diagram": "tree",
            "array_view": "flow", "queue_view": "flow", "table_view": "flow",
            "derivation": "flow", "stack": "flow", "code": "flow",
            "grid": "flow", "compare": "flow",
        }
        return _coerce_enum(value, _SIMPLE_LAYOUTS, "flow", mapping)

    @model_validator(mode="after")
    def validate_references(self) -> "SimpleScene":
        element_ids = {element.id for element in self.elements}
        self.connections = [
            conn for conn in self.connections
            if conn.source in element_ids and conn.target in element_ids
        ]
        for cue in self.cues:
            cue.targets = [t for t in cue.targets if t in element_ids]
        self.cues = [cue for cue in self.cues if cue.targets]
        return self


class SimpleVideoBrief(StrictModel):
    """简化分镜 — LLM 输出的最小 JSON 结构。

    枚举组合：3 kind × 3 action × 3 layout × 4 role = 108
    vs 完整 schema：13 × 17 × 13 × 8 = 22,984
    缩减 213 倍，大幅降低 LLM 枚举选择错误率。
    """

    title: str = Field(min_length=1, max_length=60)
    subject: str = Field(min_length=1, max_length=40)
    summary: str = Field(min_length=1, max_length=140)
    scenes: list[SimpleScene] = Field(min_length=3, max_length=16)

    @model_validator(mode="after")
    def validate_story_arc(self) -> "SimpleVideoBrief":
        if self.scenes[0].role != "hook":
            raise ValueError("第一个场景必须是 hook")
        if self.scenes[-1].role != "recap":
            raise ValueError("最后一个场景必须是 recap")
        return self


# ============================================================================
# BRIDGE: SimpleVideoBrief → VideoBrief (智能推断，零 LLM 参与)
# ============================================================================
#
# 简化 schema 只暴露 3×3×3×4 = 108 种组合给 LLM，
# 但桥接层根据 layout + role + connections + element 上下文
# 推断出完整 schema 的精确枚举值，恢复全部视觉能力。
#
# 推断规则：
#
# ── layout 推断 ──
#   tree          → tree (层次结构，BFS 布局)
#   flow + compare role → compare (左右对比布局)
#   flow + 无 connections + 有 items 的 node → array_view (格子横排)
#   flow + 无 connections + metric 多 → flow (流程图)
#   flow + 有 connections → flow (流程 + 箭头连线)
#   recap         → recap (总结网格)
#
# ── kind 推断 ──
#   node + tree layout → node (圆形节点)
#   node + flow + 有 items → cell (格子，有 data-index)
#   node + flow + value 含 "SYN"/"ACK" 等协议词 → packet (虚线数据包)
#   label + value 非空 → step (步骤，左边框强调条)
#   label + label 含 "=" 或 "→" 或 "≤" → formula (公式，serif 字体)
#   metric        → metric (数值指标)
#
# ── action 推断 ──
#   reveal        → reveal (淡入)
#   focus + targets 多个 + tree layout → traverse (逐个高亮遍历)
#   focus + targets 多个 + 有 path 连线 → highlight_path (路径高亮)
#   focus + targets 2 个 + flow layout → compare (对比强调)
#   insert + tree layout → insert (节点滑入，从父节点位置出发)
#   insert + flow + direction left/right → transfer (粒子沿边流动)
#   insert + targets 是 metric → count (数值增长)
#   insert + targets 有 value 变化 → value_change (值变化动画)
#
# ── connection.kind 推断 ──
#   tree layout → edge (实线)
#   flow + 有 connections → arrow (有向箭头)
#   recap → edge (一般无 connections)
#
# ── role 推断 ──
#   hook → hook
#   process → process
#   compare → compare
#   recap → recap
# ============================================================================


def _infer_layout(scene: SimpleScene) -> str:
    """根据简化 layout + role + connections + elements 推断精确布局。"""
    if scene.layout == "tree":
        # 检查是否更像 state_diagram：
        # 条件：(1) 节点 value 都是短状态名 (2) connections 形成环 (3) connection label 非空（触发条件）
        node_values = [e.value for e in scene.elements if e.kind == "node" and e.value]
        has_cycle = False
        if scene.connections:
            source_set = {c.source for c in scene.connections}
            target_set = {c.target for c in scene.connections}
            has_cycle = bool(source_set & target_set)
        has_condition_labels = any(c.label for c in scene.connections)
        if (node_values and len(node_values) >= 2
                and all(len(v) <= 6 for v in node_values)
                and has_cycle and has_condition_labels):
            return "state_diagram"
        return "tree"

    if scene.layout == "recap":
        return "recap"

    # flow layout — 根据 role 和内容推断更精确的布局
    if scene.role == "compare":
        return "compare"

    # 检查是否有带 items 的 node（容器类元素）
    has_container = any(e.kind == "node" and e.items for e in scene.elements)
    if has_container and not scene.connections:
        # 有 items 无 connections → 容器视图
        first_container = next(e for e in scene.elements if e.kind == "node" and e.items)
        # 根据 title 关键词推断容器类型
        title_lower = scene.title.lower()
        if any(kw in title_lower for kw in ("栈", "入栈", "出栈", "递归", "stack")):
            return "stack"
        if any(kw in title_lower for kw in ("队列", "入队", "出队", "queue")):
            return "queue_view"
        if any(kw in title_lower for kw in ("表", "table", "真值")):
            return "table_view"
        # 默认：有 items 的 node → array_view
        return "array_view"

    # 有 connections → 可能是 graph
    if scene.connections and not scene.role == "compare":
        # 如果 connections 形成环 → graph
        source_set = {c.source for c in scene.connections}
        target_set = {c.target for c in scene.connections}
        if source_set & target_set:  # 有节点既是 source 又是 target → 可能有环
            return "graph"

    # 默认 flow
    return "flow"


def _infer_kind(element: SimpleElement, layout: str) -> str:
    """根据简化 kind + layout + 内容推断精确元素类型。"""
    if element.kind == "metric":
        return "metric"

    if element.kind == "label":
        # label + value 非空 → step（步骤，有左边框强调条）
        if element.value:
            return "step"
        # label 含公式特征 → formula
        if element.label and any(ch in element.label for ch in ("=", "→", "≤", "≥", "∈", "∪", "∩", "∧", "∨", "¬")):
            return "formula"
        return "label"

    # kind == "node"
    # node + 有 items → 容器类
    if element.items:
        return "array"  # 编译器会根据 layout 的 CSS 选择排列方向

    # node + flow layout + value 含协议关键词 → packet
    if layout in ("flow", "compare"):
        protocol_keywords = ("SYN", "ACK", "FIN", "REQ", "RES", "GET", "POST", "seq", "ack")
        if element.value and any(kw in element.value for kw in protocol_keywords):
            return "packet"
        # node + flow + 短 value → cell（格子）
        if element.value and len(element.value) <= 4 and element.value.isdigit():
            return "cell"

    # node + state_diagram layout + 短 value → state（状态指示器）
    if layout == "state_diagram":
        if element.value and len(element.value) <= 6:
            return "state"

    return "node"


def _infer_action(
    cue: SimpleCue,
    scene: SimpleScene,
    layout: str,
    element_map: dict[str, SimpleElement],
) -> tuple[str, dict[str, Any]]:
    """根据简化 action + 上下文推断精确动画动作。

    返回 (action, extra_fields)，extra_fields 包含 path/new_value/result 等。
    """
    extra: dict[str, Any] = {}

    if cue.action == "reveal":
        return ("reveal", extra)

    if cue.action == "focus":
        # focus + 多 targets + tree/graph/state_diagram → traverse
        if len(cue.targets) >= 2 and layout in ("tree", "graph", "state_diagram"):
            # 检查 targets 是否形成路径（按 connections 顺序）
            target_set = set(cue.targets)
            path_nodes: list[str] = []
            visited: set[str] = set()
            for t in cue.targets:
                if t not in visited:
                    path_nodes.append(t)
                    visited.add(t)
            if len(path_nodes) >= 2:
                return ("traverse", extra)

        # focus + 2 targets + compare layout → compare action
        if len(cue.targets) == 2 and layout == "compare":
            return ("compare", extra)

        return ("focus", extra)

    # cue.action == "insert"
    # insert + targets 是 metric → count
    if all(element_map.get(t, SimpleElement(id=t, kind="node")).kind == "metric" for t in cue.targets):
        return ("count", extra)

    # insert + tree layout → insert (从父节点位置滑入，compiler 自动处理)
    if layout in ("tree", "graph", "state_diagram"):
        return ("insert", extra)

    # insert + flow + direction left/right + 有 connections → transfer
    if layout == "flow" and cue.direction in ("left", "right") and scene.connections:
        # 检查 target 是否有对应的 connection
        for t in cue.targets:
            for conn in scene.connections:
                if conn.target == t or conn.source == t:
                    return ("transfer", extra)

    # insert + flow + 无 connections → branch (展开分支)
    if layout in ("flow", "compare") and not scene.connections:
        if len(cue.targets) >= 2:
            return ("branch", extra)

    return ("insert", extra)


def _infer_conn_kind(layout: str, source_elem: SimpleElement | None, target_elem: SimpleElement | None) -> str:
    """推断 connection kind。"""
    if layout == "tree":
        return "edge"
    if layout == "state_diagram":
        return "transition"
    if layout == "graph":
        return "edge"
    # flow / compare / 其他
    return "arrow"


def bridge_simple_to_brief(simple: SimpleVideoBrief) -> VideoBrief:
    """将简化分镜智能推断映射为完整 VideoBrief。

    LLM 只输出 3×3×3×4 = 108 种组合，
    桥接层根据 layout + role + connections + element 上下文
    推断出完整 schema 的精确枚举值，恢复全部 14 种布局、13 种元素、17 种动画能力。
    """
    full_scenes: list[SceneBrief] = []

    for s in simple.scenes:
        # 1. 推断精确布局
        layout = _infer_layout(s)

        # 2. 构建 element id → element 映射
        element_map = {e.id: e for e in s.elements}

        # 3. 推断精确元素类型
        elements = [
            VisualElement(
                id=e.id,
                kind=_infer_kind(e, layout),
                label=e.label,
                value=e.value,
                items=e.items,
                detail="",
            )
            for e in s.elements
        ]

        # 4. 推断 connection kind
        connections = [
            VisualConnection(
                source=conn.source,
                target=conn.target,
                kind=_infer_conn_kind(
                    layout,
                    element_map.get(conn.source),
                    element_map.get(conn.target),
                ),
                label=conn.label,
            )
            for conn in s.connections
        ]

        # 5. 推断精确动画动作
        cues: list[AnimationCue] = []
        for c in s.cues:
            action, extra = _infer_action(c, s, layout, element_map)
            cue_kwargs: dict[str, Any] = {
                "action": action,
                "targets": c.targets,
                "keyword": c.keyword,
                "direction": c.direction,
            }
            cue_kwargs.update(extra)
            cues.append(AnimationCue(**cue_kwargs))

        # 6. 推断精确 role（当前 1:1，但可扩展）
        role = s.role
        # process + state_diagram layout → 可推断为 derivation
        if s.role == "process" and layout == "state_diagram":
            # 如果 title 含推导/证明关键词 → derivation role
            if any(kw in s.title for kw in ("推导", "证明", "变换", "归约")):
                role = "derivation"

        full_scenes.append(SceneBrief(
            role=role,
            title=s.title,
            narration=s.narration,
            layout=layout,
            elements=elements,
            connections=connections,
            cues=cues,
            callout=s.callout,
        ))

    return VideoBrief(
        title=simple.title,
        subject=simple.subject,
        summary=simple.summary,
        scenes=full_scenes,
    )
