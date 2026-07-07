"""学习事件类型常量 — 按 module 分组。

设计原则：
- 每个 module 下的事件类型字符串发布后即冻结。
- METADATA_SCHEMA 定义每 (module, event_type) 的 metadata 字段白名单。
"""

from __future__ import annotations

# ── Module 常量 ────────────────────────────────────────────────────────────────
MODULE_CHAT = "chat"
MODULE_RESOURCE = "resource"
MODULE_PATH = "path"
MODULE_QUIZ = "quiz"
MODULE_VISUALIZER = "visualizer"

ALL_MODULES: frozenset[str] = frozenset({
    MODULE_CHAT, MODULE_RESOURCE, MODULE_PATH, MODULE_QUIZ, MODULE_VISUALIZER,
})

# ── Chat 事件类型 ──────────────────────────────────────────────────────────────
CHAT_DIALOGUE = "chat_dialogue"

# ── Resource 事件类型 ──────────────────────────────────────────────────────────
RESOURCE_GENERATED = "resource_generated"
RESOURCE_VIEWED = "resource_viewed"
RESOURCE_COMPLETED = "resource_completed"
RESOURCE_FEEDBACK = "resource_feedback"

# ── Path 事件类型 ──────────────────────────────────────────────────────────────
PATH_NODE_STARTED = "path_node_started"
PATH_NODE_COMPLETED = "path_node_completed"
PATH_QUIZ_ANSWERED = "path_quiz_answered"
PATH_FEEDBACK = "path_feedback"

# ── Quiz 事件类型 ──────────────────────────────────────────────────────────────
QUIZ_SUBMITTED = "quiz_submitted"

# ── Visualizer 事件类型 ────────────────────────────────────────────────────────
VISUALIZER_RUN = "visualizer_run"

# ── 模块 → 事件类型映射 ──────────────────────────────────────────────────────
EVENT_TYPES_BY_MODULE: dict[str, frozenset[str]] = {
    MODULE_CHAT: frozenset({CHAT_DIALOGUE}),
    MODULE_RESOURCE: frozenset({RESOURCE_GENERATED, RESOURCE_VIEWED, RESOURCE_COMPLETED, RESOURCE_FEEDBACK}),
    MODULE_PATH: frozenset({PATH_NODE_STARTED, PATH_NODE_COMPLETED, PATH_QUIZ_ANSWERED, PATH_FEEDBACK}),
    MODULE_QUIZ: frozenset({QUIZ_SUBMITTED}),
    MODULE_VISUALIZER: frozenset({VISUALIZER_RUN}),
}

ALL_EVENT_TYPES: frozenset[str] = frozenset(
    et for ets in EVENT_TYPES_BY_MODULE.values() for et in ets
)

SCORED_EVENT_TYPES: frozenset[str] = frozenset({QUIZ_SUBMITTED, PATH_QUIZ_ANSWERED, PATH_NODE_COMPLETED})

# ── Metadata schema 定义 ───────────────────────────────────────────────────────
METADATA_SCHEMA: dict[tuple[str, str], list[str]] = {
    (MODULE_CHAT, CHAT_DIALOGUE): ["turn_count", "summary_md", "summary_length"],
    (MODULE_RESOURCE, RESOURCE_GENERATED): ["resource_id", "user_need", "agent_types", "agent_params", "status"],
    (MODULE_RESOURCE, RESOURCE_VIEWED): [],
    (MODULE_RESOURCE, RESOURCE_COMPLETED): [],
    (MODULE_RESOURCE, RESOURCE_FEEDBACK): ["feedback_type"],
    (MODULE_PATH, PATH_NODE_STARTED): ["path_id", "node_id"],
    (MODULE_PATH, PATH_NODE_COMPLETED): ["path_id", "node_id", "weak_knowledge_points"],
    (MODULE_PATH, PATH_QUIZ_ANSWERED): ["path_id", "node_id", "weak_knowledge_points", "outcome"],
    (MODULE_PATH, PATH_FEEDBACK): ["path_id", "node_id"],
    (MODULE_QUIZ, QUIZ_SUBMITTED): ["total_count", "correct_count", "wrong_knowledge_points"],
    (MODULE_VISUALIZER, VISUALIZER_RUN): ["language", "success", "error_message"],
}
"""每 (module, event_type) 允许写入 metadata 的字段白名单。"""
