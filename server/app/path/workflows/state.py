"""LangGraph 状态定义 — 路径模块所有工作流的状态类型。

所有 TypedDict 状态类在此集中定义，供 plan_workflow 和 learn_workflow 共用。
"""

from __future__ import annotations

from typing import Any

from typing_extensions import TypedDict


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
