"""Chat 模块数据模式定义。

包含 Agent 内部状态类型、教学图解 Schema 等。
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, Union
from typing_extensions import TypedDict

from pydantic import BaseModel, ConfigDict, Field, model_validator
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from app.chat.tools.memory import MemoryReader


# ===================================================================
# Agent 内部状态类型（TypedDict，total=False 兼容 LangGraph 增量更新）
# ===================================================================

class TutorAgentContext(BaseModel):
    """Agent 初始化上下文 — 由 service 层构造后传入 TutorAgent。

    包含用户身份、系统提示词、只读能力和功能开关。
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    user_id: int
    session_id: str
    system_prompt: str
    session_summary_context: str = ""
    file_context: str = ""
    attachment_analysis_context: str = ""
    attachment_analysis: dict[str, Any] = Field(default_factory=dict)
    attachments: list[str] = Field(default_factory=list)
    enable_search: bool = False
    need_teaching_diagram: bool = False
    diagram_mode: Literal["requested", "off"] = "off"
    preferred_diagram_type: Optional["TeachingDiagramType"] = None
    generate_video: bool = False
    resource_mode: str = "none"
    memory_reader: MemoryReader | None = None


class TutorState(TypedDict, total=False):
    """LangGraph 运行状态 — 精简版。

    移除了 planner/compile_plan/execute_step/replan 相关的复杂状态字段。
    所有字段均为可选，支持 LangGraph 增量更新。
    """

    # ---- 用户身份与附件 ----
    user_id: int  # 用户ID
    session_id: str  # 会话ID
    attachments: Optional[list[str]]  # 附件URL列表
    need_teaching_diagram: bool  # 是否生成教学图解
    enable_search: bool  # 是否启用搜索
    teaching_diagram: Optional[dict[str, Any]]  # 生成的教学图解数据
    teaching_diagram_error: Optional[str]  # 教学图解生成错误信息
    diagram_type: Optional["TeachingDiagramType"]  # 教学图解类型

    # ---- 路由与执行模式 ----
    route: str  # 路由结果
    execution_mode: str  # 执行模式
    summary_type: str  # 总结类型
    search_result: str  # 搜索节点返回的搜索结果

    # ---- 上下文信息 ----
    retrieved_profile_context: str  # Agent 本轮按需读取的用户画像，只读
    retrieved_memory_context: str  # Agent 本轮按需读取的跨会话学习事实，只读
    session_summary_context: str  # 服务层注入的旧会话摘要，只读
    file_context: str  # 文件上下文
    attachment_analysis_context: str  # 附件分析上下文
    attachment_analysis: dict[str, Any]  # 附件分析结果

    # ---- Prompt 模板 ----
    system_prompt: str  # 系统提示词

    # ---- 对话消息 ----
    messages: Annotated[list[AnyMessage], add_messages]  # 消息列表（支持增量追加）

    # ---- 终止信息 ----
    answer_text: str  # 最终回答文本
    termination_reason: str  # 终止原因


# ===================================================================
# 教学图解 Schema
# ===================================================================

TeachingDiagramType = Literal["contrast", "journey", "anatomy", "simulation"]


class TeachingDiagramModel(BaseModel):
    """教学图解模型基类。"""

    model_config = ConfigDict(extra="forbid")


class ContrastSide(TeachingDiagramModel):
    label: str = Field(min_length=1, max_length=30)
    definition: str = Field(min_length=1, max_length=160)
    signals: list[str] = Field(min_length=1, max_length=4)
    example: str = Field(min_length=1, max_length=160)


class ContrastPayload(TeachingDiagramModel):
    decision_rule: str = Field(min_length=1, max_length=240)
    left: ContrastSide
    right: ContrastSide
    scenario_conclusion: str = Field(min_length=1, max_length=240)


class JourneyStep(TeachingDiagramModel):
    title: str = Field(min_length=1, max_length=40)
    action: str = Field(min_length=1, max_length=180)
    rationale: str = Field(min_length=1, max_length=180)
    output: str = Field(min_length=1, max_length=180)
    warning: Optional[str] = Field(default=None, max_length=160)


class JourneyPayload(TeachingDiagramModel):
    goal: str = Field(min_length=1, max_length=200)
    steps: list[JourneyStep] = Field(min_length=3, max_length=6)
    result: str = Field(min_length=1, max_length=240)


class AnatomyPart(TeachingDiagramModel):
    name: str = Field(min_length=1, max_length=40)
    responsibility: str = Field(min_length=1, max_length=180)
    detail: str = Field(min_length=1, max_length=220)
    interaction_cue: Optional[str] = Field(default=None, max_length=160)


class AnatomyPayload(TeachingDiagramModel):
    subject: str = Field(min_length=1, max_length=80)
    parts: list[AnatomyPart] = Field(min_length=3, max_length=7)
    interaction_summary: str = Field(min_length=1, max_length=240)


class SimulationFrame(TeachingDiagramModel):
    stage: str = Field(min_length=1, max_length=40)
    state: str = Field(min_length=1, max_length=200)
    changed: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=200)
    learner_focus: str = Field(min_length=1, max_length=160)


class SimulationPayload(TeachingDiagramModel):
    scenario: str = Field(min_length=1, max_length=200)
    initial_state: str = Field(min_length=1, max_length=200)
    frames: list[SimulationFrame] = Field(min_length=2, max_length=6)
    result: str = Field(min_length=1, max_length=240)


class InsightCanvas(TeachingDiagramModel):
    """一次答疑对应的一张结构化教学图板。"""

    type: TeachingDiagramType
    title: str = Field(min_length=1, max_length=80)
    focus_question: str = Field(min_length=1, max_length=240)
    takeaway: str = Field(min_length=1, max_length=240)
    why_it_works: str = Field(min_length=1, max_length=400)
    pitfall: Optional[str] = Field(default=None, max_length=240)
    try_it: str = Field(min_length=1, max_length=240)
    personalization_note: Optional[str] = Field(default=None, max_length=240)
    payload: Union[ContrastPayload, JourneyPayload, AnatomyPayload, SimulationPayload]

    @model_validator(mode="after")
    def validate_payload_type(self) -> "InsightCanvas":
        expected_type = {
            "contrast": ContrastPayload,
            "journey": JourneyPayload,
            "anatomy": AnatomyPayload,
            "simulation": SimulationPayload,
        }[self.type]
        if not isinstance(self.payload, expected_type):
            raise ValueError("teaching diagram payload must match diagram type")
        return self
