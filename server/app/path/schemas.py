"""路径规划模块 Pydantic 模型。

包含请求/响应/内部状态的所有数据结构。

主要分类：
1. 请求模型 — PathRequest, PathResourceRequest
2. Agent 结构化输出 — LearningPlan, PlanNode, AgentStage
3. 响应 DTO — PathResponse, LearningPathNodeWorkspaceResponse 等
4. 工作流状态 — LearnState (LangGraph 状态图)
5. 校验函数 — validate_path_plan (阶段/节点/依赖环校验)
"""

from __future__ import annotations

from typing import Any, Literal, TYPE_CHECKING
from typing_extensions import TypedDict

from pydantic import BaseModel, Field, model_validator

if TYPE_CHECKING:
    from app.infra.models import PathNode, PathNodeTutorial, PathNodeQuestion, PathNodeResource

# ======================================================================
# 请求模型
# ======================================================================


# 路径创建请求 — POST /path-plan 的请求体
class PathRequest(BaseModel):
    """新学习路径创建请求。"""

    goal: str = Field(description="学习目标")
    topic: str = Field(default="", description="学习主题")
    current_knowledge: list[str] = Field(default_factory=list, description="当前已掌握的知识点")
    preferences: dict[str, Any] = Field(default_factory=dict, description="学习偏好")


# 节点教程 DTO — 用于工作区响应和资源生成请求
class LearningPathTutorialDTO(BaseModel):
    id: int
    tutorial_type: str
    version_no: int
    based_on_tutorial_id: int | None = None
    title: str
    summary: str | None = None
    content_markdown: str
    knowledge_points: list[str] = Field(default_factory=list)
    weak_knowledge_points: list[str] = Field(default_factory=list)
    created_at: str

    # 从 ORM 模型构建教程 DTO
    @classmethod
    def from_model(cls, tutorial: PathNodeTutorial) -> LearningPathTutorialDTO:
        return cls(
            id=tutorial.id,
            tutorial_type=tutorial.tutorial_type,
            version_no=tutorial.version_no,
            based_on_tutorial_id=tutorial.based_on_tutorial_id,
            title=tutorial.title,
            summary=tutorial.summary,
            content_markdown=tutorial.content_markdown,
            knowledge_points=list(tutorial.knowledge_points or []),
            weak_knowledge_points=list(tutorial.weak_knowledge_points or []),
            created_at=tutorial.created_at.isoformat() if tutorial.created_at else "",
        )


# 路径节点资源生成请求 — 统一参数模型
class PathResourceRequest(BaseModel):
    """路径节点资源生成请求 — 统一参数。

    用于 mindmap / code / ppt / reading / cartoon 五种资源类型。

    核心字段：
    - user_id: 用户 ID
    - path_id: 路径 ID
    - node_id: 节点 ID
    - profile: 用户画像
    - tutorial: 教程内容

    上下文字段（由 PathService 填充）：
    - username: 用户名（文件路径用）
    - path_title / path_goal: 路径标题/目标
    - node_title / node_key / difficulty: 节点信息
    - knowledge_points / weak_knowledge_points: 知识点
    """

    user_id: int
    path_id: int
    node_id: int
    profile: dict[str, Any] = Field(default_factory=dict)
    tutorial: LearningPathTutorialDTO | None = None

    # 上下文字段（由 PathService 查询填充）
    username: str = ""
    path_title: str = ""
    path_goal: str = ""
    node_title: str = ""
    node_key: str = ""
    difficulty: str = "beginner"


# ======================================================================
# Agent 结构化输出模型
# ======================================================================


# 学习效果快照 — 用于路径优化决策
class LearningSignalSnapshot(BaseModel):
    """学习效果摘要 — 路径调整用的聚合信号。"""

    average_score: float | None = Field(default=None, description="平均测验分数 0-100")
    weak_topics: list[str] = Field(default_factory=list, description="薄弱知识点")
    preferred_resources: list[str] = Field(default_factory=list, description="偏好资源类型")
    negative_feedback: list[str] = Field(default_factory=list, description="负面反馈摘要")
    completed_resource_count: int = Field(default=0)
    viewed_resource_count: int = Field(default=0)
    active_minutes: int = Field(default=0)
    recommendations: list[str] = Field(default_factory=list, description="系统调整建议")


# 节点测验题目 DTO
class LearningPathQuestionDTO(BaseModel):
    id: int
    question_no: int
    round_no: int
    mode: str
    type: str
    question: str
    choice: dict[str, Any] = Field(default_factory=dict)
    answer: str
    response: str | None = None
    analysis: str | None = None
    knowledge_points: list[str] = Field(default_factory=list)
    is_correct: bool | None = None

    # 从 ORM 模型构建题目 DTO
    @classmethod
    def from_model(cls, question: PathNodeQuestion) -> LearningPathQuestionDTO:
        return cls(
            id=question.id,
            question_no=question.question_no,
            round_no=question.round_no,
            mode=question.mode,
            type=question.type,
            question=question.question,
            choice=dict(question.choice or {}),
            answer=question.answer,
            response=question.response,
            analysis=question.analysis,
            knowledge_points=list(question.knowledge_points or []),
            is_correct=question.is_correct,
        )


# 节点资源 DTO — 辅助学习资源
class LearningPathResourceDTO(BaseModel):
    id: int
    resource_type: str
    version_no: int
    title: str
    content_format: str
    content_text: str | None = None
    content_json: dict[str, Any] | None = None
    summary: str | None = None
    status: str = "completed"
    error_message: str | None = None
    input_data: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str

    # 从 ORM 模型构建资源 DTO
    @classmethod
    def from_model(cls, resource: PathNodeResource) -> LearningPathResourceDTO:
        return cls(
            id=resource.id,
            resource_type=resource.resource_type,
            version_no=resource.version_no,
            title=resource.title,
            content_format=resource.content_format,
            content_text=resource.content_text,
            content_json=resource.content_json,
            summary=resource.summary,
            status=resource.status or "completed",
            error_message=resource.error_message,
            input_data=resource.input_json,
            metadata=dict(resource.metadata_json or {}),
            created_at=resource.created_at.isoformat() if resource.created_at else "",
        )


# 路径节点 DTO
class LearningPathNodeDTO(BaseModel):
    id: int
    node_id: str
    stage_id: str
    title: str
    status: str
    priority: int
    attempt_count: int
    difficulty: str | None = None
    prerequisites: list[str] = Field(default_factory=list)

    # 从 ORM 模型构建节点 DTO
    @classmethod
    def from_model(cls, node: PathNode) -> LearningPathNodeDTO:
        return cls(
            id=node.id,
            node_id=node.node_id,
            stage_id=node.stage_id,
            title=node.title,
            status=node.status,
            priority=node.priority,
            attempt_count=node.attempt_count,
            difficulty=node.difficulty,
            prerequisites=list(node.prerequisites or []),
        )


# 路径概览响应 — GET /path-plan/active 等的响应体
class PathResponse(BaseModel):
    id: int
    module: str
    title: str
    goal: str
    topic: str | None = None
    overall_progress: int
    status: str
    current_node_key: str | None = None
    stages: list[AgentStage] = Field(default_factory=list)
    nodes: list[LearningPathNodeDTO] = Field(default_factory=list)
    created_at: str
    updated_at: str


# 路径历史列表项
class LearningPathHistoryItem(BaseModel):
    id: int
    title: str
    goal: str
    topic: str | None = None
    overall_progress: int
    status: str
    updated_at: str


# 节点工作区响应 — GET /nodes/{id}/workspace 的完整响应
class LearningPathNodeWorkspaceResponse(BaseModel):
    path: PathResponse
    node: LearningPathNodeDTO
    current_tutorial: LearningPathTutorialDTO | None = None
    tutorials: list[LearningPathTutorialDTO] = Field(default_factory=list)
    resources: list[LearningPathResourceDTO] = Field(default_factory=list)
    current_round: int = 0
    quiz_available: bool = False


# 测验轮次响应 — GET /nodes/{id}/questions
class PathQuizRoundResponse(BaseModel):
    node_id: int
    tutorial_id: int | None = None
    round_no: int
    questions: list[LearningPathQuestionDTO] = Field(default_factory=list)


# 测验答案提交项
class PathQuizAnswerItem(BaseModel):
    question_id: int
    response: str


# 测验提交请求 — POST /nodes/{id}/quiz-submit
class PathQuizSubmitRequest(BaseModel):
    answers: list[PathQuizAnswerItem] = Field(default_factory=list, min_length=5, max_length=5)


# 测验提交响应 — 评分结果和下一步指引
class PathQuizSubmitResponse(BaseModel):
    node_id: int
    round_no: int
    score: int
    passed: bool
    outcome: Literal["completed", "remediation", "completed_with_gaps"]
    weak_knowledge_points: list[str] = Field(default_factory=list)
    next_node_id: int | None = None
    current_tutorial_id: int | None = None


# Agent 生成的单道题目
class AgentQuestionItem(BaseModel):
    question: str = Field(description="题干")
    choice: dict[str, str] = Field(description="选项映射，如 {'A': '选项内容', 'B': '选项内容'}，至少2个选项")
    answer: str = Field(description="正确答案，如 A")
    analysis: str = Field(default="", description="题目解析")
    knowledge_points: list[str] = Field(default_factory=list, description="涉及知识点")
    type: str = Field(default="single_choice", description="题型")

    @model_validator(mode="after")
    def validate_choice(self) -> "AgentQuestionItem":
        if len(self.choice) < 2:
            raise ValueError(f"choice 必须至少包含2个选项，当前只有 {len(self.choice)} 个")
        return self


# Agent 生成的题目集 — LLM 结构化输出
class AgentQuestionSet(BaseModel):
    questions: list[AgentQuestionItem] = Field(default_factory=list, min_length=0, max_length=5)


# 规划节点 — LLM 输出的节点定义
class PlanNode(BaseModel):
    """规划 Agent 输出的单个路径节点。"""

    node_id: str = Field(description="节点唯一标识")
    stage_id: str = Field(description="阶段标识")
    title: str = Field(description="节点标题")
    prerequisites: list[str] = Field(default_factory=list, description="前置节点 ID")
    difficulty: str = Field(default="intermediate", description="难度等级")
    priority: int = Field(default=0, description="优先级")


# 规划阶段 — LLM 输出的阶段定义
class AgentStage(BaseModel):
    """规划 Agent 输出的阶段。"""

    stage_id: str = Field(description="阶段标识，如'stage-1'")
    title: str = Field(description="阶段标题")


# 学习计划 — PathPlannerAgent 的完整输出
class LearningPlan(BaseModel):
    """规划 Agent 的结构化输出。"""

    title: str = Field(description="路径标题")
    stages: list[AgentStage] = Field(min_length=1, description="宏观阶段骨架列表，至少1个阶段")
    nodes: list[PlanNode] = Field(min_length=1, description="所有阶段的具体学习节点列表，至少1个节点")


# 路径学习评估响应
class PathLearningEvaluationResponse(BaseModel):
    """路径内学习效果评估响应。"""

    path_id: int
    overall_progress: float = 0.0
    current_node_key: str | None = None
    signal_snapshot: LearningSignalSnapshot = Field(default_factory=LearningSignalSnapshot)
    needs_optimization: bool = False
    optimization_tips: list[str] = Field(default_factory=list)


# ======================================================================
# LangGraph 工作流状态定义
# ======================================================================

# 节点学习工作流状态 — LangGraph 状态图的 total=False TypedDict
class LearnState(TypedDict, total=False):
    """节点学习工作流的状态结构。

    每次 API 调用会填充对应 phase 的字段子集，图根据 ``phase`` 路由，
    并在节点流水线推进过程中逐步修改状态。

    标记 ``total=False`` 的字段为可选 — 图在执行过程中按需初始化。
    """

    # ── 服务层注入字段 ──────────────────────────────────────────────
    user_id: int
    """已认证的用户 ID。"""
    node_id: int
    """PathNode 主键 — 当前正在学习的节点。"""
    phase: str
    """路由键：``'start'``（开始学习）| ``'questions'``（生成题目）| ``'quiz'``（提交测验）| ``'resource'``（生成资源）。"""
    session: Any
    """AsyncSession — 由 PathService 注入，供数据库访问节点使用。"""

    # ── 上下文加载字段（由 ``node_load_context`` 填充）────────────
    node: Any
    """PathNode ORM 实例。"""
    path: Any
    """LearningPath ORM 实例。"""
    tutorials: list[Any]
    """当前节点的所有 PathNodeTutorial 实例，按版本号排序。"""
    current_tutorial: Any
    """当前激活的 PathNodeTutorial，不存在时为 None。"""
    profile_markdown: str
    """预渲染的学习者画像 Markdown 文本。"""
    username: str
    """当前用户名 — 由 ``node_load_context`` 从 ``User`` 解析，用于构建节点资源文件保存路径。"""

    # ── 阶段输入字段 ──────────────────────────────────────────────
    quiz_answers: list[dict]
    """用户提交的答案：``[{'question_id': int, 'response': str}]``。"""
    resource_type: str
    """辅助资源类型：``'mindmap'`` | ``'code'`` | ``'reading'`` | ``'ppt'`` | ``'content'``。"""

    # ── 教程参数 ──────────────────────────────────────────────────
    tutorial_type: str
    """教程类型：``'primary'``（主教程）| ``'remediation'``（补救教程）| ``'reinforced'``（强化教程）。"""
    weak_knowledge_points: list[str]
    """学习者在测验中暴露出的薄弱知识点。"""
    based_on_tutorial_id: int | None
    """强化教程所基于的主教程 ID。"""

    # ── 生成输出字段 ──────────────────────────────────────────────
    tutorial: Any
    """新创建的 PathNodeTutorial ORM 实例。"""
    tutorial_content: str
    """LLM 生成的教程原始 Markdown 内容。"""
    generated_questions: list[dict]
    """持久化前的原始题目字典列表。"""
    score: int
    """测验得分（0-5 分）。"""
    passed: bool
    """测验是否通过（得分 ≥ 通过线）。"""
    outcome: str
    """节点推进结果：``'completed'``（通过）| ``'remediation'``（需补救）| ``'completed_with_gaps'``（有缺陷通过）。"""
    next_node_id: int | None
    """完成后下一个可用节点的 ID。"""
    resource_result: Any
    """资源生成的 AgentResult 结果。"""
    resource_dto: dict
    """序列化后的资源 DTO，用于 API 响应。"""

    # ── 测验轮次追踪 ──────────────────────────────────────────────
    round_no: int
    """当前测验轮次编号。"""
    quiz_questions: list[Any]
    """当前轮次的 PathNodeQuestion ORM 实例列表。"""

    # ── 错误处理 ──────────────────────────────────────────────────
    error: str | None
    """错误信息 — 设置后图应中止执行。"""


# ======================================================================
# 路径规划结构校验
# ======================================================================

# 合法的难度等级
VALID_DIFFICULTIES: tuple[str, ...] = ("beginner", "intermediate", "advanced")


# 路径规划校验失败异常
class PathPlanValidationError(ValueError):
    """路径规划结构校验失败 — LLM 输出不安全，不应持久化。"""


# 校验路径规划结构完整性，不通过则拒绝持久化
def validate_path_plan(plan: LearningPlan) -> None:
    """校验生成的路径规划，不合格时抛出 PathPlanValidationError。

    校验项：
    1. stages 和 nodes 非空
    2. 阶段 ID 唯一且非空
    3. 节点 ID 唯一且非空
    4. 节点引用的 stage_id 存在
    5. 难度等级合法
    6. 前置依赖节点存在且不自引用
    7. 无依赖环
    8. 至少一个无前置依赖的起始节点
    9. 每个阶段至少包含一个节点
    """
    if not plan.stages:
        raise PathPlanValidationError("学习路径必须包含至少一个阶段")
    if not plan.nodes:
        raise PathPlanValidationError("学习路径必须包含至少一个学习节点")

    # 校验阶段 ID 唯一性
    stage_ids: set[str] = set()
    for stage in plan.stages:
        if not stage.stage_id.strip():
            raise PathPlanValidationError("阶段 stage_id 不能为空")
        if stage.stage_id in stage_ids:
            raise PathPlanValidationError(f"阶段 ID 重复: {stage.stage_id}")
        stage_ids.add(stage.stage_id)

    # 校验节点：ID 唯一性、阶段引用、难度等级、构建邻接表
    node_ids: set[str] = set()
    adjacency: dict[str, list[str]] = {}
    for node in plan.nodes:
        if not node.node_id.strip():
            raise PathPlanValidationError("节点 node_id 不能为空")
        if node.node_id in node_ids:
            raise PathPlanValidationError(f"节点 ID 重复: {node.node_id}")
        if node.stage_id not in stage_ids:
            raise PathPlanValidationError(f"节点 {node.node_id} 引用了不存在的阶段: {node.stage_id}")
        if node.difficulty and node.difficulty not in VALID_DIFFICULTIES:
            raise PathPlanValidationError(
                f"节点 {node.node_id} 的 difficulty 必须是 {', '.join(VALID_DIFFICULTIES)} 之一"
            )
        node_ids.add(node.node_id)
        adjacency[node.node_id] = list(node.prerequisites or [])

    # 校验前置依赖：存在性 + 不自引用
    for node_id, prerequisites in adjacency.items():
        for prerequisite_id in prerequisites:
            if prerequisite_id == node_id:
                raise PathPlanValidationError(f"节点 {node_id} 不能依赖自身")
            if prerequisite_id not in node_ids:
                raise PathPlanValidationError(f"节点 {node_id} 引用了不存在的前置节点: {prerequisite_id}")

    # 校验无依赖环
    _assert_no_dependency_cycle(adjacency)

    # 校验至少有一个起始节点
    root_nodes = [node for node in plan.nodes if not node.prerequisites]
    if not root_nodes:
        raise PathPlanValidationError("学习路径必须至少包含一个无前置依赖 of 起始节点")

    # 校验每个阶段至少包含一个节点
    _validate_stage_node_coverage(plan, stage_ids)


# 校验每个阶段至少包含一个节点
def _validate_stage_node_coverage(plan: LearningPlan, stage_ids: set[str]) -> None:
    """校验每个阶段至少包含一个节点。"""
    stages_with_nodes: set[str] = set()
    for node in plan.nodes:
        stages_with_nodes.add(node.stage_id)
    empty_stages = stage_ids - stages_with_nodes
    if empty_stages:
        raise PathPlanValidationError(
            f"以下阶段没有节点: {', '.join(sorted(empty_stages))}"
        )


# DFS 检测依赖环，发现环时抛出异常
def _assert_no_dependency_cycle(adjacency: dict[str, list[str]]) -> None:
    """DFS 检测依赖环，发现环时抛出异常。"""
    visiting: set[str] = set()
    visited: set[str] = set()

    # 递归 DFS 访问节点，检测环
    def visit(node_id: str, trail: list[str]) -> None:
        if node_id in visited:
            return
        if node_id in visiting:
            # 检测到环，输出环路径
            cycle = " -> ".join([*trail, node_id])
            raise PathPlanValidationError(f"学习路径依赖存在环: {cycle}")

        visiting.add(node_id)
        for prerequisite_id in adjacency.get(node_id, []):
            visit(prerequisite_id, [*trail, node_id])
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in adjacency:
        visit(node_id, [])


__all__ = [
    # Request
    "PathRequest",
    # Agent output
    "PlanNode",
    "AgentStage",
    "LearningPlan",
    "AgentQuestionItem",
    "AgentQuestionSet",
    # Signal
    "LearningSignalSnapshot",
    # State
    "LearnState",
    # Validation
    "VALID_DIFFICULTIES",
    "PathPlanValidationError",
    "validate_path_plan",
    # Response
    "LearningPathQuestionDTO",
    "LearningPathResourceDTO",
    "LearningPathTutorialDTO",
    "LearningPathNodeDTO",
    "PathResponse",
    "LearningPathHistoryItem",
    "LearningPathNodeWorkspaceResponse",
    "PathQuizRoundResponse",
    "PathQuizSubmitRequest",
    "PathQuizSubmitResponse",
    "PathLearningEvaluationResponse",
]
